import os
import shutil
import librosa
import soundfile as sf
from fastapi import UploadFile
from src.tablature.model_utils import load_model, predict_notes

# Cache the model in memory
_MODEL = None

def get_model():
    global _MODEL
    if _MODEL is None:
        _MODEL = load_model()
    return _MODEL



def transcribe_audio(file_path: str):
    """
    Orchestrates transcription process from an existing processed file path.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Processed audio file not found at {file_path}")
        
    # Load model and transcribe
    model = get_model()
    notes = predict_notes(model, file_path)
    return notes