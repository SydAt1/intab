from fastapi import FastAPI, Request
from src.api.routes import auth, transcription, upload
from src.fretboard import fretboard_api
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import os

app = FastAPI(title="InTab API")

from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api")
app.include_router(upload.router, prefix="/api")
app.include_router(transcription.router, prefix="/api")
app.include_router(fretboard_api.router)
from src.api.routes import audio, chords, quiz
app.include_router(audio.router, prefix="/api")
app.include_router(chords.router, prefix="/api")
app.include_router(quiz.router, prefix="/api/quiz")

@app.on_event("startup")
async def startup_event():
    from src.core import minio_client
    # minio_client.ensure_bucket_exists()

@app.get("/api/health")
def read_root():
    return {"message": "API is running"}


# Jinja2 Templates

_base_dir = os.path.dirname(os.path.dirname(__file__))
_templates_dir = os.path.join(_base_dir, "frontend", "web", "templates")
templates = Jinja2Templates(directory=_templates_dir)


# Clean-URL page routes (no .html extension)


@app.get("/")
async def page_index(request: Request):
    return templates.TemplateResponse(request, "index.html")

@app.get("/chords")
async def page_chords(request: Request):
    return templates.TemplateResponse(request, "chords.html")

@app.get("/fretboard")
async def page_fretboard(request: Request):
    return templates.TemplateResponse(request, "fretboard.html")

@app.get("/history")
async def page_history(request: Request):
    return templates.TemplateResponse(request, "history.html")

@app.get("/search")
async def page_search(request: Request):
    return templates.TemplateResponse(request, "search.html")

@app.get("/login")
async def page_login(request: Request):
    return templates.TemplateResponse(request, "login.html")

@app.get("/quiz")
async def page_quiz(request: Request):
    return templates.TemplateResponse(request, "quiz.html")

@app.get("/register")
async def page_register(request: Request):
    return templates.TemplateResponse(request, "register.html")

@app.get("/sidenav")
async def page_sidenav(request: Request):
    return templates.TemplateResponse(request, "sidenav.html")

@app.get("/tablature")
async def page_tablature(request: Request):
    return templates.TemplateResponse(request, "tablature.html")

@app.get("/forgot-password")
async def page_forgot_password(request: Request):
    return templates.TemplateResponse(request, "forgot_password.html")

@app.get("/reset-password")
async def page_reset_password(request: Request, token: str = None):
    return templates.TemplateResponse(request, "reset_password.html", {"token": token})


# Static file mounts (CSS, JS, assets) — must come AFTER page routes

_web_dir = os.path.join(_base_dir, "frontend", "web")

_css_dir = os.path.join(_web_dir, "css")
if os.path.exists(_css_dir):
    app.mount("/css", StaticFiles(directory=_css_dir), name="css")

_js_dir = os.path.join(_web_dir, "js")
if os.path.exists(_js_dir):
    app.mount("/js", StaticFiles(directory=_js_dir), name="js")

_static_dir = os.path.join(_web_dir, "static")
if os.path.exists(_static_dir):
    app.mount("/static", StaticFiles(directory=_static_dir), name="static")