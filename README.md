# Audio Tablature Studio (InTab)

A comprehensive full-stack web application designed for guitarists and musicians. This application allows users to upload audio files, isolate the guitar tracks, transcribe the audio into precise guitar tablature, and recognize chords, all powered by advanced deep learning models.

## 🚀 Key Features

* **Audio Stem Separation:** Integrates with Facebook's Demucs to isolate guitar stems from complex, multi-instrumental audio mixes. Users can also precisely clip audio using start and end timestamps.
* **AI-Powered Tablature Transcription:** Utilizes a custom-trained Convolutional Recurrent Neural Network (CRNN) to convert raw acoustic and electric guitar audio directly into readable tablature.
* **Chord Recognition:** Employs a dedicated machine learning classifier to analyze audio segments, recognize chords, and visualize them using dynamic fretboard diagrams.
* **Interactive Dashboard & Visualization:** Features a beautifully designed, premium dark-themed frontend interface for users to visually engage with their generated tablature and chords.
* **User Management & History:** Secure JWT-based authentication system. Users have personalized histories where they can save, search, and manage their past transcriptions and analyzed audio files.

## 🛠️ Tech Stack

### Backend & Infrastructure
* **Framework:** FastAPI (Python 3.13+)
* **Database (Relational):** Supabase PostgreSQL via SQLAlchemy ORM
* **Database (Object Storage):** Supabase Storage (S3-compatible) for secure audio file and stem storage
* **Authentication:** PyJWT, Passlib, UUID-based Session Management
* **Containerization:** Docker & Docker Compose

### Machine Learning & Audio Processing
* **Deep Learning Framework:** PyTorch, Torchaudio
* **Stem Separation:** Demucs
* **Audio Processing:** Librosa, SoundFile, Torchcodec
* **Modeling:** Custom CRNN (Transcription), Scikit-Learn (Chord Classification)

### Frontend
* **Core:** HTML5, CSS3, Vanilla JavaScript
* **Templating:** Jinja2 (served via FastAPI `TemplateResponse` with clean URLs)
* **Styling:** Custom "Premium Dark" aesthetic with flex/grid layouts and CSS animations
* **Architecture:** Component-based UI with dynamic DOM manipulation (Sidebar injections, interactive scroll-snapping)

---

## 📂 Project Structure

```text
├── frontend/
│   └── web/
│       ├── templates/       # Jinja2 HTML templates (served via clean URL routes)
│       ├── css/             # Stylesheets (mounted at /css)
│       ├── js/              # Page-specific JS modules (mounted at /js)
│       └── static/          # Shared JS utilities & assets (mounted at /static)
├── src/
│   ├── api/                 # FastAPI route implementations (auth, upload, audio, transcription, chords)
│   ├── core/                # Core configuration, environment variables, security
│   ├── db/                  # SQLAlchemy models and database connections
│   ├── fretboard/           # Visualization logic and ML models for the guitar fretboard
│   ├── tablature/           # Transcription logic and CRNN model inference
│   ├── app.py               # FastAPI app factory, Jinja2 template routes, static mounts
│   └── main.py              # CLI Bootstrap
├── test/                    # Unit testing and validation scripts
├── Dockerfile               # Official container definition 
├── docker-compose.yml       # Docker network and deployment configuration
├── .env                     # Environment variables (Credentials & Config)
├── pyproject.toml           # Project metadata and dependencies
└── README.md                # Project documentation
```

---

## 🚦 Quick Start

### 1. Prerequisites
You can run this project locally on your machine, or completely isolated inside a Docker container.
* **If running locally:** Python 3.13+, FFmpeg installed natively
* **If using Docker (Recommended):** Docker Desktop installed
* **Cloud Services**: A properly configured Supabase Project (Database and Storage Bucket)

### 2. Configuration
Create a `.env` file in the root directory. Ensure you populate the necessary Supabase PostgreSQL and S3 configurations in it:
```env
# Database (IMPORTANT: Use the IPv4 connection pool proxy for Docker support on Mac)
DB_USER=postgres.[project-id]
DB_PASSWORD=yourpassword
DB_NAME=postgres
DB_HOST=aws-[region].pooler.supabase.com
DB_PORT=6543

# Storage
S3_ENDPOINT=https://[project-id].storage.supabase.co/storage/v1/s3
S3_ACCESS_KEY=your_key
S3_SECRET_KEY=your_secret_key
S3_BUCKET=intab-audio
```

### 3. Running via Docker (Recommended)
This approach completely eliminates manual setup. Docker automatically installs system dependencies like `ffmpeg` inside the container for you alongside your Python environment!
```bash
docker-compose up --build
```
* **Frontend UI**: `http://localhost:8000/`
* **API Documentation**: `http://localhost:8000/docs`

### 4. Running via terminal (Local / Native)
If you prefer running outside of Docker (assuming you've setup virtual environments via `uv` or `pip`):
```bash
# Example utilizing 'uv' pipeline
uv run uvicorn src.app:app --host 0.0.0.0 --port 8000
```

---

## ☁️ Deployment Notes

* **Render Deployment:** This application is completely configured to be deployed straight from GitHub to Render. When deploying as a Web Service on Render, simply choose the **Docker** Runtime setting rather than Python so Render natively parses the `Dockerfile` and successfully installs `ffmpeg`.
* **Reverse Proxy:** For production environments natively, run Uvicorn behind a reverse proxy such as Nginx.
* **Environment Security:** Never commit `.env` files containing sensitive database or S3 credentials to version control. Let continuous integration tools inject them securely at runtime.
