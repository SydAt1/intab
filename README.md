# Audio Tablature Studio

A comprehensive full-stack web application designed for guitarists and musicians. This application allows users to upload audio files, isolate the guitar tracks, transcribe the audio into precise guitar tablature, and recognize chords—all powered by advanced deep learning models.

## 🚀 Key Features

* **Audio Stem Separation:** Integrates with Facebook's Demucs to isolate guitar stems from complex, multi-instrumental audio mixes. Users can also precisely clip audio using start and end timestamps.
* **AI-Powered Tablature Transcription:** Utilizes a custom-trained Convolutional Recurrent Neural Network (CRNN) to convert raw acoustic and electric guitar audio directly into readable tablature.
* **Chord Recognition:** Employs a dedicated machine learning classifier to analyze audio segments, recognize chords, and visualize them using dynamic fretboard diagrams.
* **Interactive Dashboard & Visualization:** Features a beautifully designed, premium dark-themed frontend interface for users to visually engage with their generated tablature and chords.
* **User Management & History:** Secure JWT-based authentication system. Users have personalized histories where they can save, search, and manage their past transcriptions and analyzed audio files.

## 🛠️ Tech Stack

### Backend & Infrastructure
* **Framework:** FastAPI (Python 3.13+)
* **Database (Relational):** PostgreSQL via SQLAlchemy ORM
* **Database (Object Storage):** MinIO (S3-compatible) for secure audio file and stem storage
* **Authentication:** PyJWT, Passlib

### Machine Learning & Audio Processing
* **Deep Learning Framework:** PyTorch, Torchaudio
* **Stem Separation:** Demucs
* **Audio Processing:** Librosa, SoundFile, Torchcodec
* **Modeling:** Custom CRNN (Transcription), Scikit-Learn (Chord Classification)

### Frontend
* **Core:** HTML5, CSS3, Vanilla JavaScript
* **Styling:** Custom "Premium Dark" aesthetic with flex/grid layouts and CSS animations
* **Architecture:** Component-based UI with dynamic DOM manipulation (Sidebar injections, interactive scroll-snapping)

---

## 📂 Project Structure

```text
├── frontend/
│   └── web/                 # Static HTML/CSS/JS assets for the UI and components
├── src/
│   ├── api/                 # FastAPI route implementations (auth, upload, audio, transcription, chords)
│   ├── core/                # Core configuration, environment variables, security
│   ├── db/                  # SQLAlchemy models and MinIO storage configuration
│   ├── fretboard/           # Visualization logic and ML models for the guitar fretboard
│   ├── tablature/           # Transcription logic and CRNN model inference
│   ├── app.py               # FastAPI application factory and router registration
│   └── main.py              # CLI Bootstrap
├── test/                    # Unit testing and validation scripts
├── .env                     # Environment variables (Credentials & Config)
├── pyproject.toml           # Project metadata and dependencies
└── README.md                # Project documentation
```

---

## 🚦 Quick Start

### 1. Prerequisites
* **Python**: 3.13 or newer
* **Database**: PostgreSQL server running
* **Storage**: MinIO instance running

### 2. Configuration
Create a `.env` file in the root directory (using the provided `.env.sample` as a reference if available). Ensure you populate:
* Database credentials (`DATABASE_URL` or equivalent)
* MinIO settings (`MINIO_ENDPOINT`, `MINIO_ACCESS_KEY`, `MINIO_SECRET_KEY`, `MINIO_BUCKET`)
* JWT Secret Keys

### 3. Installation
**Using Poetry (Recommended):**
```bash
poetry install
```

**Without Poetry (Manual via pip):**
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows use: .venv\Scripts\activate
pip install -r requirements.txt
```

### 4. Running the Application
Launch the Uvicorn development server:
```bash
uvicorn src.app:app --reload --host 0.0.0.0 --port 8000
```
* **Frontend UI**: `http://localhost:8000/` (Static assets are mounted at the root URL)
* **API Documentation (Swagger UI)**: `http://localhost:8000/docs`

---

## ☁️ Deployment Notes
* **Reverse Proxy:** For production environments, run Uvicorn behind a reverse proxy such as Nginx.
* **Process Manager:** Utilize a process manager like Gunicorn with Uvicorn worker classes to handle production traffic safely.
* **Environment Security:** Never commit `.env` files containing sensitive database or S3 credentials to version control.

## 🤝 Contributing
1. Open an issue to discuss proposed feature requests or potential bugs.
2. Submit a Pull Request containing a clear description of the changes and the rationale behind them.

