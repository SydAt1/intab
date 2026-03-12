from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, Query
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
import tempfile
import os
import uuid
import json

from src.chords.chords import recognize_chords
from src.core import minio_client
from src.db.connection import get_db
from src.db.models import User
from src.db.audio_model import AudioFile
from src.db.chord_model import Chord
from src.api.dependencies import get_current_user
from src.core import minio_client

router = APIRouter(prefix="/chords", tags=["chords"])

ALLOWED_CONTENT_TYPES = ["audio/mpeg", "audio/wav", "audio/flac", "audio/ogg", "audio/mp4"]
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB

@router.post("/recognize")
async def recognize_chords_api(
    file: UploadFile = File(...),
    tab_name: str = Form(None),
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
        raise HTTPException(status_code=400, detail="File too large. Maximum size is 50MB.")
        
    temp_dir = tempfile.mkdtemp()
    temp_file_path = None
    
    try:
        # Generate storage key and upload to MinIO
        _, ext = os.path.splitext(file.filename)
        if not ext:
            ext = ".wav" # Default
            
        file_id = str(uuid.uuid4())
        storage_key = f"chords/{current_user.id}/{file_id}{ext}"
        
        minio_client.upload_audio(file_bytes, storage_key, file.content_type)
        audio_url = minio_client.get_presigned_url(storage_key)
        
        # Write bytes to temporary file for librosa to process
        temp_file_path = os.path.join(temp_dir, f"temp_upload_{file.filename}")
        with open(temp_file_path, "wb") as f:
            f.write(file_bytes)
            
        # Process the audio file to get chords
        chords, duration = recognize_chords(temp_file_path)
        
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
            "audio_url": minio_client.get_presigned_url(r.storage_key),
            "chords": chords_data
        })
    return results
