from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import List, Optional
from datetime import datetime, date
import os
import tempfile
import uuid

from src.db.connection import get_db
from src.db.models import User
from src.db.audio_model import AudioFile
from src.db.tablature_model import Tablature
from src.api.dependencies import get_current_user
from src.core import s3_client

from pydantic import BaseModel

class PathUploadRequest(BaseModel):
    file_path: str
    tab_name: Optional[str] = None

# Transcription services
from src.tablature.upload_service import process_upload
from src.tablature.service import transcribe_audio
from src.tablature.visualization import generate_ascii_tab

router = APIRouter(prefix="/audio", tags=["audio"])

ALLOWED_CONTENT_TYPES = ["audio/mpeg", "audio/wav", "audio/flac", "audio/ogg", "audio/mp4"]
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100 MB

@router.post("/upload")
async def upload_audio_file(
    file: UploadFile = File(...),
    tab_name: Optional[str] = Form(None),
    trim_start: Optional[float] = Form(None),
    trim_end: Optional[float] = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Uploads an audio file and saves it to S3 with a DB record."""
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Allowed: {', '.join(ALLOWED_CONTENT_TYPES)}"
        )
        
    # Read file to check size and upload later
    file_bytes = await file.read()
    file_size = len(file_bytes)
    
    if file_size > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="file too large")
        
    # Trim audio if timestamps are provided
    if trim_start is not None and trim_end is not None:
        try:
            import librosa
            import soundfile as sf
            from io import BytesIO
            
            # Load audio from bytes
            y, sr = librosa.load(BytesIO(file_bytes), sr=44100)
            
            # Convert timestamps to samples
            start_sample = int(trim_start * sr)
            end_sample = int(trim_end * sr)
            
            # Slice audio
            y_trimmed = y[start_sample:end_sample]
            
            # Write back to bytes
            out_io = BytesIO()
            sf.write(out_io, y_trimmed, sr, format='WAV')
            file_bytes = out_io.getvalue()
            file_size = len(file_bytes)
            
            # Always extension .wav after processing
            file.filename = os.path.splitext(file.filename)[0] + ".wav"
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Failed to trim audio: {str(e)}")
        
    # Generate unique ID, filename, and storage key
    file_id = str(uuid.uuid4())
    _, ext = os.path.splitext(file.filename)
    if not ext:
        ext = ".wav" # Default
        
    storage_key = f"uploads/{current_user.id}/{file_id}{ext}"
    
    # Upload to S3
    s3_client.upload_audio(file_bytes, storage_key, file.content_type)
    
    # Default tab name if none provided
    final_tab_name = tab_name if tab_name else os.path.splitext(file.filename)[0]
    
    # Create Database Record
    new_audio = AudioFile(
        id=file_id,
        user_id=current_user.id,
        original_filename=file.filename,
        storage_key=storage_key,
        file_size_bytes=file_size,
        tab_name=final_tab_name,
        status="pending"
    )
    
    db.add(new_audio)
    db.commit()
    db.refresh(new_audio)
    
    return {
        "id": new_audio.id,
        "original_filename": new_audio.original_filename,
        "tab_name": new_audio.tab_name,
        "status": new_audio.status,
        "uploaded_at": new_audio.uploaded_at
    }

@router.post("/upload-from-path")
async def upload_audio_from_path(
    payload: PathUploadRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Uploads a server-local file (e.g., from URL fetch) to S3 and creates a DB record."""
    if not os.path.exists(payload.file_path):
        raise HTTPException(status_code=400, detail="File not found")
        
    with open(payload.file_path, "rb") as f:
        file_bytes = f.read()
        
    file_size = len(file_bytes)
    if file_size > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="file too large")
        
    file_id = str(uuid.uuid4())
    original_filename = os.path.basename(payload.file_path)
    _, ext = os.path.splitext(original_filename)
    if not ext:
        ext = ".wav"
        
    storage_key = f"uploads/{current_user.id}/{file_id}{ext}"
    content_type = "audio/wav" if ext.lower() == ".wav" else "audio/mpeg"
    
    s3_client.upload_audio(file_bytes, storage_key, content_type)
    
    final_tab_name = payload.tab_name if payload.tab_name else original_filename.rsplit(".", 1)[0]
    
    new_audio = AudioFile(
        id=file_id,
        user_id=current_user.id,
        original_filename=original_filename,
        storage_key=storage_key,
        file_size_bytes=file_size,
        tab_name=final_tab_name,
        status="pending"
    )
    
    db.add(new_audio)
    db.commit()
    db.refresh(new_audio)
    
    return {
        "id": new_audio.id,
        "original_filename": new_audio.original_filename,
        "tab_name": new_audio.tab_name,
        "status": new_audio.status,
        "uploaded_at": new_audio.uploaded_at
    }

@router.post("/{audio_id}/transcribe")
async def transcribe_audio_file(
    audio_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Triggers the transcription process for a specific audio file."""
    audio_record = db.query(AudioFile).filter(
        AudioFile.id == audio_id,
        AudioFile.user_id == current_user.id
    ).first()
    
    if not audio_record:
        raise HTTPException(status_code=404, detail="Audio file not found")
        
    if audio_record.status == "done":
        # Pre-existing tablature
        tab_record = db.query(Tablature).filter(Tablature.audio_file_id == audio_id).first()
        return {
            "audio_id": audio_id,
            "tab_name": audio_record.tab_name,
            "tab_content": tab_record.tab_content if tab_record else None,
            "status": "done"
        }
        
    # Update state to processing
    audio_record.status = "processing"
    db.commit()
    
    temp_dir = tempfile.mkdtemp()
    temp_file_path = None
    processed_path = None
    
    try:
        # Download raw audio from S3
        file_bytes = s3_client.download_audio(audio_record.storage_key)
        
        # Write bytes to temporary file to simulate UploadFile flow behavior
        temp_file_path = os.path.join(temp_dir, f"raw_{audio_record.id}.wav")
        with open(temp_file_path, "wb") as f:
            f.write(file_bytes)
            
        # Create a mock FastApi UploadFile to pass to process_upload
        with open(temp_file_path, "rb") as f:
            # We must wrap in UploadFile to reuse process_upload
            from fastapi import UploadFile as FastApiUploadFile
            import starlette.datastructures as datastructures
            upload_dummy = FastApiUploadFile(
                filename=f"audio_{audio_record.id}.wav",
                file=f
            )
            processed_path = process_upload(upload_dummy, temp_dir)
            
        # Do the actual transcription using CRNN model logic
        notes = transcribe_audio(processed_path)
        
        # --- NEW CODE: Upload isolated guitar stem back to S3 ---
        base_key, ext = os.path.splitext(audio_record.storage_key)
        new_storage_key = f"{base_key}_processed{ext}"
        
        with open(processed_path, "rb") as f:
            processed_bytes = f.read()
            
        # Determine content type (usually wav since process_upload forces it)
        content_type = "audio/wav" if processed_path.endswith(".wav") else "audio/mpeg"
        
        s3_client.upload_audio(processed_bytes, new_storage_key, content_type)
        
        # Update audio_record to point to the processed audio
        audio_record.storage_key = new_storage_key
        # --- END NEW CODE ---
        
        # Convert notes to tab
        ascii_tab = generate_ascii_tab(notes)
        
        # Save tablature
        new_tab = Tablature(
            audio_file_id=audio_record.id,
            user_id=current_user.id,
            tab_content=ascii_tab
        )
        db.add(new_tab)
        
        # Mark as done
        audio_record.status = "done"
        db.commit()
        db.refresh(new_tab)
        
        return {
            "audio_id": audio_id,
            "tab_name": audio_record.tab_name,
            "tab_content": new_tab.tab_content,
            "status": "done"
        }
        
    except Exception as e:
        audio_record.status = "failed"
        db.commit()
        raise HTTPException(status_code=500, detail=f"Transcription failed: {str(e)}")
        
    finally:
        # Cleanup temp files
        if temp_file_path and os.path.exists(temp_file_path):
            os.remove(temp_file_path)
        if processed_path and os.path.exists(processed_path):
            os.remove(processed_path)
        if os.path.exists(temp_dir):
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)

@router.patch("/{audio_id}/rename")
async def rename_audio_file(
    audio_id: str,
    payload: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Updates the user-defined tablature name."""
    if "tab_name" not in payload:
        raise HTTPException(status_code=400, detail="Missing tab_name in JSON body")
        
    audio_record = db.query(AudioFile).filter(
        AudioFile.id == audio_id,
        AudioFile.user_id == current_user.id
    ).first()
    
    if not audio_record:
        raise HTTPException(status_code=404, detail="Audio file not found")
        
    audio_record.tab_name = payload["tab_name"]
    db.commit()
    db.refresh(audio_record)
    
    return {
        "id": audio_record.id,
        "tab_name": audio_record.tab_name,
        "updated": True
    }

@router.delete("/{audio_id}")
async def delete_audio_file(
    audio_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Permanently deletes an audio file, its S3 object, and related records."""
    audio_record = db.query(AudioFile).filter(
        AudioFile.id == audio_id,
        AudioFile.user_id == current_user.id
    ).first()

    if not audio_record:
        raise HTTPException(status_code=404, detail="Audio file not found")

    # 1. Delete related tablature record (if any)
    tab_record = db.query(Tablature).filter(Tablature.audio_file_id == audio_id).first()
    if tab_record:
        db.delete(tab_record)

    # 2. Delete related chord record (if any)
    from src.db.chord_model import Chord
    chord_record = db.query(Chord).filter(Chord.audio_file_id == audio_id).first()
    if chord_record:
        db.delete(chord_record)

    # 3. Delete file(s) from S3
    try:
        s3_client.delete_audio(audio_record.storage_key)
    except Exception:
        pass  # Storage key may already be gone

    # Also try the original upload key if storage_key was updated to _processed
    if "_processed" in audio_record.storage_key:
        try:
            original_key = audio_record.storage_key.replace("_processed", "")
            s3_client.delete_audio(original_key)
        except Exception:
            pass

    # 4. Delete the audio record itself
    db.delete(audio_record)
    db.commit()

    return {"deleted": True, "id": audio_id}

@router.get("/my-uploads")
async def get_my_uploads(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Returns all uploads for the logged-in user, newest first."""
    records = db.query(AudioFile).filter(
        AudioFile.user_id == current_user.id,
        AudioFile.storage_key.startswith("uploads/")
    ).order_by(AudioFile.uploaded_at.desc()).all()
    
    return [
        {
            "id": r.id,
            "original_filename": r.original_filename,
            "tab_name": r.tab_name,
            "status": r.status,
            "uploaded_at": r.uploaded_at
        }
        for r in records
    ]

@router.get("/{audio_id}/result")
async def get_transcription_result(
    audio_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Returns the generated tablature and an audio URL if done."""
    audio_record = db.query(AudioFile).filter(
        AudioFile.id == audio_id,
        AudioFile.user_id == current_user.id
    ).first()
    
    if not audio_record:
        raise HTTPException(status_code=404, detail="Audio file not found")
        
    if audio_record.status != "done":
        return {
            "status": audio_record.status,
            "tab_content": None
        }
        
    tab_record = db.query(Tablature).filter(Tablature.audio_file_id == audio_id).first()
    # Use local streaming proxy instead of broken S3 presigned URLs
    audio_url = f"/api/audio/{audio_id}/stream"
    
    return {
        "status": "done",
        "tab_name": audio_record.tab_name,
        "tab_content": tab_record.tab_content if tab_record else None,
        "audio_url": audio_url
    }

@router.get("/{audio_id}/stream")
async def stream_audio(
    audio_id: str,
    token: str = Query(..., description="JWT auth token"),
    db: Session = Depends(get_db),
):
    """Streams the audio file from S3 storage directly to the browser.
    Uses a query-param token because <audio> elements cannot send Auth headers."""
    from src.auth.jwt_utils import verify_token
    payload = verify_token(token)
    if payload is None or payload.get("sub") is None:
        raise HTTPException(status_code=401, detail="Invalid token")
    user = db.query(User).filter(User.username == payload["sub"]).first()
    if not user:
        raise HTTPException(status_code=401, detail="Invalid token")

    audio_record = db.query(AudioFile).filter(
        AudioFile.id == audio_id,
        AudioFile.user_id == user.id
    ).first()
    
    if not audio_record:
        raise HTTPException(status_code=404, detail="Audio file not found")
    
    try:
        file_bytes = s3_client.download_audio(audio_record.storage_key)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve audio: {str(e)}")
    
    # Determine content type from storage key extension
    ext = os.path.splitext(audio_record.storage_key)[1].lower()
    content_type_map = {
        ".wav": "audio/wav",
        ".mp3": "audio/mpeg",
        ".flac": "audio/flac",
        ".ogg": "audio/ogg",
        ".m4a": "audio/mp4",
    }
    content_type = content_type_map.get(ext, "audio/wav")
    
    return Response(
        content=file_bytes,
        media_type=content_type,
        headers={
            "Content-Disposition": f'inline; filename="{audio_record.original_filename}"',
            "Accept-Ranges": "bytes",
        }
    )


@router.get("/search")
async def search_uploads(
    name: Optional[str] = None,
    filename: Optional[str] = None,
    from_date: Optional[date] = None,
    to_date: Optional[date] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Searches audio files belonging to the logged-in user."""
    query = db.query(AudioFile).filter(
        AudioFile.user_id == current_user.id,
        AudioFile.storage_key.startswith("uploads/")
    )
    
    if name:
        query = query.filter(AudioFile.tab_name.ilike(f"%{name}%"))
        
    if filename:
        query = query.filter(AudioFile.original_filename.ilike(f"%{filename}%"))
        
    if from_date:
        query = query.filter(AudioFile.uploaded_at >= from_date)
        
    if to_date:
        query = query.filter(AudioFile.uploaded_at <= to_date)
        
    records = query.order_by(AudioFile.uploaded_at.desc()).all()
    
    return [
        {
            "id": r.id,
            "original_filename": r.original_filename,
            "tab_name": r.tab_name,
            "status": r.status,
            "uploaded_at": r.uploaded_at
        }
        for r in records
    ]
