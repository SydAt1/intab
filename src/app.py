from fastapi import FastAPI
from src.api.routes import auth
from src.fretboard import fretboard_api
from fastapi.staticfiles import StaticFiles
import os

app = FastAPI(title="Int6 API")

app.include_router(auth.router)
app.include_router(fretboard_api.router)

@app.get("/api/health")
def read_root():
    return {"message": "API is running"}

# Serve static files (HTML, CSS, JS)
# This must be after API routes to avoid conflicts
static_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend", "web")
if os.path.exists(static_dir):
    app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")
else:
    print(f"Warning: Static directory not found at {static_dir}")
