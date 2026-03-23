# import os
# import tempfile
# import librosa
# import shutil
# import soundfile as sf
# from fastapi import UploadFile

# def preprocess_audio(file_path: str, output_path: str):
#     """
#     Apply noise reduction and distortion reduction preprocessing.
#     """
#     # Simply load and save for now, could add more advanced librosa-based processing
#     y, sr = librosa.load(file_path, sr=22050)
    
#     # Simple normalization as a form of preprocessing
#     y = librosa.util.normalize(y)
    
#     sf.write(output_path, y, sr)
#     return output_path

# def process_upload(upload_file: UploadFile, temp_dir: str = None):
#     """
#     Handles the file saving and triggers preprocessing.
#     Returns the path to the processed audio file.
#     """
#     if temp_dir is None:
#         temp_dir = tempfile.gettempdir()
        
#     os.makedirs(temp_dir, exist_ok=True)
    
#     raw_path = os.path.join(temp_dir, f"raw_{upload_file.filename}")
#     processed_path = os.path.join(temp_dir, f"proc_{upload_file.filename}")
    
#     # Save uploaded bytes
#     with open(raw_path, "wb") as f:
#         shutil.copyfileobj(upload_file.file, f)
        
#     try:
#         # Preprocess
#         preprocess_audio(raw_path, processed_path)
#         return processed_path
        
#     finally:
#         # Cleanup original raw file, keep the processed one for the transcription step
#         if os.path.exists(raw_path):
#             os.remove(raw_path)

import os
import tempfile
import librosa
import shutil
import soundfile as sf
from pathlib import Path
from fastapi import UploadFile


def separate_guitar(file_path: str, output_dir: str) -> str:
    """
    Use Demucs htdemucs_6s to extract the guitar stem from a mixed audio file.
    Returns the path to the isolated guitar stem.
    """
    import subprocess

    subprocess.run(
        [
            "python", "-m", "demucs",
            "--two-stems", "guitar",   # only output guitar + other, skips unused stems
            "-n", "htdemucs_6s",       # 6-stem model with dedicated guitar stem
            "--out", output_dir,
            file_path,
        ],
        check=True,
    )

    # Demucs saves output to: <output_dir>/htdemucs_6s/<track_name>/guitar.wav
    track_name = Path(file_path).stem
    guitar_stem_path = os.path.join(output_dir, "htdemucs_6s", track_name, "guitar.wav")

    if not os.path.exists(guitar_stem_path):
        raise FileNotFoundError(
            f"Demucs did not produce a guitar stem at expected path: {guitar_stem_path}"
        )

    return guitar_stem_path


def preprocess_audio(file_path: str, output_path: str, target_sr: int = 22050) -> str:
    """
    Normalize and resample audio to target sample rate.
    Call this after guitar separation to clean up the stem before transcription.
    """
    y, sr = librosa.load(file_path, sr=target_sr)
    y = librosa.util.normalize(y)
    sf.write(output_path, y, sr)
    return output_path


def process_upload(upload_file: UploadFile, temp_dir: str = None) -> str:
    """
    Full pipeline:
      1. Save uploaded file
      2. Separate guitar stem via Demucs
      3. Normalize + resample
      4. Return path to processed guitar audio, ready for tablature model
    """
    if temp_dir is None:
        temp_dir = tempfile.gettempdir()

    os.makedirs(temp_dir, exist_ok=True)

    raw_path = os.path.join(temp_dir, f"raw_{upload_file.filename}")
    processed_path = os.path.join(temp_dir, f"proc_{upload_file.filename}")

    # 1. Save uploaded bytes
    with open(raw_path, "wb") as f:
        shutil.copyfileobj(upload_file.file, f)

    try:
        # 2. Separate guitar stem
        print("Running Demucs guitar separation (this may take 1-3 min on CPU)...")
        guitar_stem_path = separate_guitar(raw_path, temp_dir)

        # 3. Normalize + resample
        preprocess_audio(guitar_stem_path, processed_path)

        return processed_path

    finally:
        # Cleanup raw upload, Demucs intermediate files
        if os.path.exists(raw_path):
            os.remove(raw_path)


def process_url_upload(url: str, temp_dir: str = None) -> str:
    """
    Download audio from a YouTube/TikTok URL via yt-dlp, then run through
    the same Demucs guitar separation + normalization pipeline.
    Returns the path to the processed audio file.
    """
    import subprocess
    import glob

    if temp_dir is None:
        temp_dir = tempfile.gettempdir()

    os.makedirs(temp_dir, exist_ok=True)

    output_template = os.path.join(temp_dir, "raw_ytdlp.%(ext)s")
    processed_path = os.path.join(temp_dir, "proc_ytdlp.wav")

    # 1. Download audio with yt-dlp
    result = subprocess.run(
        [
            "yt-dlp",
            "--extract-audio",
            "--audio-format", "wav",
            "--audio-quality", "0",
            "--no-playlist",
            "--max-filesize", "50m",
            "-o", output_template,
            url,
        ],
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        stderr = result.stderr or ""
        if "Video unavailable" in stderr or "Private video" in stderr:
            raise ValueError(
                "This video is unavailable or private. Please check the URL and try again."
            )
        raise RuntimeError(f"yt-dlp failed: {stderr.strip() or 'Unknown error'}")

    # 2. Locate the downloaded file
    matches = glob.glob(os.path.join(temp_dir, "raw_ytdlp.*"))
    if not matches:
        raise RuntimeError("yt-dlp finished but no downloaded file was found.")

    raw_path = matches[0]

    try:
        # 3. Separate guitar stem
        print("Running Demucs guitar separation on downloaded audio (this may take 1-3 min on CPU)...")
        guitar_stem_path = separate_guitar(raw_path, temp_dir)

        # 4. Normalize + resample
        preprocess_audio(guitar_stem_path, processed_path)

        return processed_path

    finally:
        # Cleanup raw yt-dlp download
        if os.path.exists(raw_path):
            os.remove(raw_path)