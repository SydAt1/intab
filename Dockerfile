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

# Install Python dependencies first to leverage Docker layer cache.
# torch + demucs are large — this step can take several minutes.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application source
COPY . .

# Expose FastAPI port
EXPOSE 8000

CMD ["uvicorn", "src.app:app", "--host", "0.0.0.0", "--port", "8000"]
