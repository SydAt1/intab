FROM python:3.13-slim

WORKDIR /app

# System dependencies:
#   ffmpeg        - required by demucs (audio decoding/encoding) and yt-dlp
#   libsndfile1   - required by soundfile / librosa for audio I/O
#   libpq-dev     - required to compile psycopg2 (PostgreSQL adapter, C extension)
#   build-essential + gcc + python3-dev - C/C++ toolchain for compiled Python extensions
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libsndfile1 \
    libpq-dev \
    gcc \
    g++ \
    python3-dev \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install PyTorch ecosystem from CPU-only index FIRST to avoid pulling
# CUDA-linked binaries from default PyPI.
RUN pip install --no-cache-dir \
    torch==2.10.0 \
    torchaudio==2.10.0 \
    --index-url https://download.pytorch.org/whl/cpu

# Install remaining Python dependencies (leverages Docker layer cache).
# torch/torchaudio are already satisfied from above, so pip skips them.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Patch torchaudio.save to use soundfile instead of torchcodec (which needs CUDA).
# The .pth file auto-imports the patch at Python startup, so it also applies
# to demucs subprocesses (python -m demucs) that call torchaudio.save().
COPY patches/fix_torchaudio_save.py /usr/local/lib/python3.13/site-packages/fix_torchaudio_save.py
RUN echo "import fix_torchaudio_save" > /usr/local/lib/python3.13/site-packages/fix_torchaudio_save.pth

# Pre-download the htdemucs_6s model weights so they are baked into the image
# and never fetched at runtime (avoids network failures during inference).
RUN python -c "from demucs.pretrained import get_model; get_model('htdemucs_6s')"

# Copy the rest of the application source
COPY . .

# Expose FastAPI port
EXPOSE 8000

CMD ["uvicorn", "src.app:app", "--host", "0.0.0.0", "--port", "8000"]
