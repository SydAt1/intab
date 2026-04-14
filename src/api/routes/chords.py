from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, Query
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
import tempfile
import os
import uuid
import json

from src.chords.chords import recognize_chords
from src.tablature.upload_service import separate_guitar, preprocess_audio
from src.core import s3_client
from src.db.connection import get_db
from src.db.models import User
from src.db.audio_model import AudioFile
from src.db.chord_model import Chord
from src.api.dependencies import get_current_user

router = APIRouter(prefix="/chords", tags=["chords"])

ALLOWED_CONTENT_TYPES = ["audio/mpeg", "audio/wav", "audio/flac", "audio/ogg", "audio/mp4"]
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100 MB

@router.post("/recognize")
async def recognize_chords_api(
    file: UploadFile = File(...),
    tab_name: str = Form(None),
    use_guitar_separation: bool = Form(False),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Endpoint to recognize chords from an uploaded audio file.
    Returns JSON with chord timestamps.
    """
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Allowed: {', '.join(ALLOWED_CONTENT_TYPES)}"
        )
        
    file_bytes = await file.read()
    file_size = len(file_bytes)
    
    if file_size > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="file too large")
        
    temp_dir = tempfile.mkdtemp()
    temp_file_path = None
    
    try:
        # Generate storage key and upload to S3
        _, ext = os.path.splitext(file.filename)
        if not ext:
            ext = ".wav" # Default
            
        file_id = str(uuid.uuid4())
        storage_key = f"chords/{current_user.id}/{file_id}{ext}"
        
        s3_client.upload_audio(file_bytes, storage_key, file.content_type)
        audio_url = s3_client.get_presigned_url(storage_key)
        
        # Write bytes to temporary file for librosa to process
        temp_file_path = os.path.join(temp_dir, f"temp_upload_{file.filename}")
        with open(temp_file_path, "wb") as f:
            f.write(file_bytes)

        # Optionally isolate guitar stem via Demucs before chord recognition
        audio_for_chords = temp_file_path
        if use_guitar_separation:
            print("Running Demucs guitar separation for chord recognition...")
            guitar_stem_path = separate_guitar(temp_file_path, temp_dir)
            processed_path = os.path.join(temp_dir, f"proc_{file.filename}")
            preprocess_audio(guitar_stem_path, processed_path)
            audio_for_chords = processed_path

        # Process the audio file to get chords
        chords, duration = recognize_chords(audio_for_chords)
        
        # Save to database
        final_tab_name = tab_name if tab_name else os.path.splitext(file.filename)[0]
        
        new_audio = AudioFile(
            id=file_id,
            user_id=current_user.id,
            original_filename=file.filename,
            storage_key=storage_key,
            file_size_bytes=file_size,
            tab_name=final_tab_name,
            status="done"
        )
        db.add(new_audio)
        
        new_chord = Chord(
            audio_file_id=file_id,
            user_id=current_user.id,
            chord_data_json=json.dumps(chords)
        )
        db.add(new_chord)
        db.commit()
        
        return JSONResponse(content={
            "status": "success",
            "file": file.filename,
            "storage_key": storage_key,
            "audio_url": audio_url,
            "duration": duration,
            "chords": chords
        })
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Chord recognition failed: {str(e)}")
        
    finally:
        # Cleanup temp file
        if temp_file_path and os.path.exists(temp_file_path):
            os.remove(temp_file_path)
        if os.path.exists(temp_dir):
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)

@router.get("/my-chords")
async def get_my_chords(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Returns all chord recognitions for the logged-in user, newest first."""
    records = db.query(AudioFile).filter(
        AudioFile.user_id == current_user.id,
        AudioFile.storage_key.startswith("chords/")
    ).order_by(AudioFile.uploaded_at.desc()).all()
    
    results = []
    for r in records:
        chord_record = db.query(Chord).filter(Chord.audio_file_id == r.id).first()
        chords_data = json.loads(chord_record.chord_data_json) if chord_record else []
        results.append({
            "id": r.id,
            "original_filename": r.original_filename,
            "tab_name": r.tab_name,
            "status": r.status,
            "uploaded_at": r.uploaded_at,
            "audio_url": s3_client.get_presigned_url(r.storage_key),
            "chords": chords_data
        })
    return results

@router.delete("/{chord_audio_id}")
async def delete_chord_record(
    chord_audio_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Permanently deletes a chord recognition, its audio from S3, and DB records."""
    audio_record = db.query(AudioFile).filter(
        AudioFile.id == chord_audio_id,
        AudioFile.user_id == current_user.id
    ).first()

    if not audio_record:
        raise HTTPException(status_code=404, detail="Chord record not found")

    # Delete related chord data
    chord_record = db.query(Chord).filter(Chord.audio_file_id == chord_audio_id).first()
    if chord_record:
        db.delete(chord_record)

    # Delete file from S3
    try:
        s3_client.delete_audio(audio_record.storage_key)
    except Exception:
        pass

    # Delete the audio record
    db.delete(audio_record)
    db.commit()

    return {"deleted": True, "id": chord_audio_id}

from pydantic import BaseModel
from typing import Optional

class PathRecognizeRequest(BaseModel):
    file_path: str
    tab_name: Optional[str] = None
    use_guitar_separation: bool = False

@router.post("/recognize-from-path")
async def recognize_chords_from_path(
    payload: PathRecognizeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Recognize chords from a file that was already downloaded to disk
    (e.g. via the /upload/url endpoint). Accepts a file_path instead of
    an uploaded file, but otherwise follows the same pipeline.
    """
    if not os.path.exists(payload.file_path):
        raise HTTPException(status_code=400, detail="File not found at the given path.")

    temp_dir = tempfile.mkdtemp()
    try:
        # Read file for S3 storage
        with open(payload.file_path, "rb") as f:
            file_bytes = f.read()

        file_size = len(file_bytes)
        if file_size > MAX_FILE_SIZE:
            raise HTTPException(status_code=400, detail="file too large")

        original_filename = os.path.basename(payload.file_path)
        _, ext = os.path.splitext(original_filename)
        if not ext:
            ext = ".wav"

        file_id = str(uuid.uuid4())
        storage_key = f"chords/{current_user.id}/{file_id}{ext}"

        content_type = "audio/wav" if ext.lower() == ".wav" else "audio/mpeg"
        s3_client.upload_audio(file_bytes, storage_key, content_type)
        audio_url = s3_client.get_presigned_url(storage_key)

        # Optionally isolate guitar stem
        audio_for_chords = payload.file_path
        if payload.use_guitar_separation:
            print("Running Demucs guitar separation for chord recognition (URL upload)...")
            guitar_stem_path = separate_guitar(payload.file_path, temp_dir)
            processed_path = os.path.join(temp_dir, f"proc_url_{file_id}.wav")
            preprocess_audio(guitar_stem_path, processed_path)
            audio_for_chords = processed_path

        # Process chords
        chords, duration = recognize_chords(audio_for_chords)

        # Save to database
        final_tab_name = payload.tab_name if payload.tab_name else original_filename.rsplit(".", 1)[0]

        new_audio = AudioFile(
            id=file_id,
            user_id=current_user.id,
            original_filename=original_filename,
            storage_key=storage_key,
            file_size_bytes=file_size,
            tab_name=final_tab_name,
            status="done"
        )
        db.add(new_audio)

        new_chord = Chord(
            audio_file_id=file_id,
            user_id=current_user.id,
            chord_data_json=json.dumps(chords)
        )
        db.add(new_chord)
        db.commit()

        return JSONResponse(content={
            "status": "success",
            "file": original_filename,
            "storage_key": storage_key,
            "audio_url": audio_url,
            "duration": duration,
            "chords": chords
        })

    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Chord recognition failed: {str(e)}")
    finally:
        if os.path.exists(temp_dir):
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)
