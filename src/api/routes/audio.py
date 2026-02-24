from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, Query
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
from src.core import minio_client

# Transcription services
from src.tablature.upload_service import process_upload
from src.tablature.service import transcribe_audio
from src.tablature.visualization import generate_ascii_tab

router = APIRouter(prefix="/audio", tags=["audio"])

ALLOWED_CONTENT_TYPES = ["audio/mpeg", "audio/wav", "audio/flac", "audio/ogg", "audio/mp4"]
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB

@router.post("/upload")
async def upload_audio_file(
    file: UploadFile = File(...),
    tab_name: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Uploads an audio file and saves it to MinIO with a DB record."""
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Allowed: {', '.join(ALLOWED_CONTENT_TYPES)}"
        )
        
    # Read file to check size and upload later
    file_bytes = await file.read()
    file_size = len(file_bytes)
    
    if file_size > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File too large. Maximum size is 50MB.")
        
    # Generate unique ID, filename, and storage key
    file_id = str(uuid.uuid4())
    _, ext = os.path.splitext(file.filename)
    if not ext:
        ext = ".wav" # Default
        
    storage_key = f"uploads/{current_user.id}/{file_id}{ext}"
    
    # Upload to MinIO
    minio_client.upload_audio(file_bytes, storage_key, file.content_type)
    
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
        # Download raw audio from MinIO
        file_bytes = minio_client.download_audio(audio_record.storage_key)
        
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
            os.rmdir(temp_dir)

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

@router.get("/my-uploads")
async def get_my_uploads(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Returns all uploads for the logged-in user, newest first."""
    records = db.query(AudioFile).filter(
        AudioFile.user_id == current_user.id
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
    audio_url = minio_client.get_presigned_url(audio_record.storage_key)
    
    return {
        "status": "done",
        "tab_name": audio_record.tab_name,
        "tab_content": tab_record.tab_content if tab_record else None,
        "audio_url": audio_url
    }

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
    query = db.query(AudioFile).filter(AudioFile.user_id == current_user.id)
    
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
