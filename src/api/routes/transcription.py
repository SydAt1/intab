import tempfile
from fastapi import APIRouter, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from src.tablature.service import transcribe_audio
from src.tablature.visualization import generate_ascii_tab, generate_fretboard_plot_base64

router = APIRouter(prefix="/transcription", tags=["transcription"])

class TranscriptionRequest(BaseModel):
    file_path: str

@router.post("/transcribe")
async def transcribe(request: TranscriptionRequest):
    """
    Endpoint to transcribe an already preprocessed audio file to tablature.
    Requires passing the JSON object `{"file_path": "/path"}` returned from /upload/audio
    """
    file_path = request.file_path
    
    if not file_path or not isinstance(file_path, str):
        raise HTTPException(status_code=400, detail="Missing or invalid file_path in request body.")
        
    try:
        # Extract notes
        notes = transcribe_audio(file_path)
        
        # Generate visual representations
        ascii_tab = generate_ascii_tab(notes)
        plot_base64 = generate_fretboard_plot_base64(notes)
        
        return JSONResponse(content={
            "status": "success",
            "message": "Audio transcribed successfully.",
            "notes": notes,
            "visuals": {
                "ascii_tab": ascii_tab,
                # "fretboard_plot_base64": plot_base64
            }
        })
        
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
