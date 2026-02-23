from fastapi import APIRouter, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse
from src.tablature.upload_service import process_upload

router = APIRouter(prefix="/upload", tags=["upload"])

@router.post("/audio")
async def upload_audio(file: UploadFile = File(...)):
    """
    Endpoint to upload an audio file and run preprocessing (e.g. noise reduction).
    Returns the file path for subsequent use in transcription.
    """
    if not file.filename.endswith(('.mp3', '.wav', '.ogg', '.flac', '.m4a')):
        raise HTTPException(status_code=400, detail="Invalid file type. Only audio files are supported.")
        
    try:
        processed_path = process_upload(file)
        
        return JSONResponse(content={
            "status": "success",
            "message": "Audio uploaded and preprocessed successfully.",
            "file_path": processed_path
        })
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
