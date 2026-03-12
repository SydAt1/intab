from fastapi.testclient import TestClient
from src.app import app
import json
import os
import wave

# Create a small valid WAV file for testing
with wave.open("test.wav", "wb") as f:
    f.setnchannels(1)
    f.setsampwidth(2)
    f.setframerate(44100)
    f.writeframes(b'\x00' * 44100) # 1 second of silence

client = TestClient(app)

response = client.post(
    "/api/chords/recognize",
    files={"file": ("test.wav", open("test.wav", "rb"), "audio/wav")}
)

print(f"Status Code: {response.status_code}")
if response.status_code == 200:
    data = response.json()
    print(f"Duration: {data.get('duration')}")
    print(f"Number of chords: {len(data.get('chords', []))}")
    print(f"Storage Key: {data.get('storage_key')}")
    print(f"Audio URL: {data.get('audio_url')[:50]}...") # truncated for brevity
else:
    print(f"Error: {response.text}")

os.remove("test.wav")
