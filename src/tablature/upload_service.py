import os
import tempfile
import librosa
import shutil
import soundfile as sf
from fastapi import UploadFile

def preprocess_audio(file_path: str, output_path: str):
    """
    Apply noise reduction and distortion reduction preprocessing.
    """
    # Simply load and save for now, could add more advanced librosa-based processing
    y, sr = librosa.load(file_path, sr=22050)
    
    # Simple normalization as a form of preprocessing
    y = librosa.util.normalize(y)
    
    sf.write(output_path, y, sr)
    return output_path

def process_upload(upload_file: UploadFile, temp_dir: str = None):
    """
    Handles the file saving and triggers preprocessing.
    Returns the path to the processed audio file.
    """
    if temp_dir is None:
        temp_dir = tempfile.gettempdir()
        
    os.makedirs(temp_dir, exist_ok=True)
    
    raw_path = os.path.join(temp_dir, f"raw_{upload_file.filename}")
    processed_path = os.path.join(temp_dir, f"proc_{upload_file.filename}")
    
    # Save uploaded bytes
    with open(raw_path, "wb") as f:
        shutil.copyfileobj(upload_file.file, f)
        
    try:
        # Preprocess
        preprocess_audio(raw_path, processed_path)
        return processed_path
        
    finally:
        # Cleanup original raw file, keep the processed one for the transcription step
        if os.path.exists(raw_path):
            os.remove(raw_path)
