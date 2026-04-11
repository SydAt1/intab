from urllib.parse import urlparse

from fastapi import APIRouter, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from src.tablature.upload_service import process_upload, process_url_upload

router = APIRouter(prefix="/upload", tags=["upload"])

ALLOWED_HOSTS = {
    "youtube.com", "www.youtube.com", "youtu.be",
    "tiktok.com", "www.tiktok.com", "vm.tiktok.com",
}

MAX_FILE_SIZE = 100 * 1024 * 1024  # 100 MB


class URLUploadRequest(BaseModel):
    url: str


@router.post("/audio")
async def upload_audio(file: UploadFile = File(...)):
    """
    Endpoint to upload an audio file and run preprocessing (e.g. noise reduction).
    Returns the file path for subsequent use in transcription.
    """
    if not file.filename.endswith(('.mp3', '.wav', '.ogg', '.flac', '.m4a')):
        raise HTTPException(status_code=400, detail="Invalid file type. Only audio files are supported.")
        
    file_bytes = await file.read()
    if len(file_bytes) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="file too large")
    await file.seek(0)
        
    try:
        processed_path = process_upload(file)
        
        return JSONResponse(content={
            "status": "success",
            "message": "Audio uploaded and preprocessed successfully.",
            "file_path": processed_path
        })
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/url")
async def upload_from_url(payload: URLUploadRequest):
    """
    Accept a YouTube or TikTok URL, download the audio via yt-dlp,
    and run it through the same Demucs + preprocessing pipeline.
    """
    # Validate hostname
    try:
        parsed = urlparse(payload.url)
        hostname = parsed.hostname or ""
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid URL format.")

    if hostname not in ALLOWED_HOSTS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported URL. Only YouTube and TikTok links are allowed."
        )

    try:
        processed_path = process_url_upload(payload.url)

        return JSONResponse(content={
            "status": "success",
            "message": "Audio downloaded and preprocessed successfully.",
            "file_path": processed_path
        })

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
