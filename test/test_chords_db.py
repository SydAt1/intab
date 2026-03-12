from fastapi.testclient import TestClient
from src.app import app
import json
import os
import wave

client = TestClient(app)

# 1. Login to get token
login_data = {"username": "testuser", "password": "mypassword"}
response = client.post("/api/login", json=login_data)
if response.status_code != 200:
    print(f"Login failed: {response.text}")
    exit(1)
    
token = response.json()["access_token"]
headers = {"Authorization": f"Bearer {token}"}

# 2. Create mock audio
with wave.open("test.wav", "wb") as f:
    f.setnchannels(1)
    f.setsampwidth(2)
    f.setframerate(44100)
    f.writeframes(b'\x00' * 44100)

# 3. Post to recognize
response = client.post(
    "/api/chords/recognize",
    files={"file": ("test.wav", open("test.wav", "rb"), "audio/wav")},
    data={"tab_name": "My Great Song Chords"},
    headers=headers
)

print(f"Recognize Status: {response.status_code}")
if response.status_code == 200:
    data = response.json()
    print(f"Recognized {len(data['chords'])} chords.")
else:
    print(f"Recognize Error: {response.text}")
    
# 4. Get my-chords
response = client.get("/api/chords/my-chords", headers=headers)
print(f"My-Chords Status: {response.status_code}")
if response.status_code == 200:
    chords_list = response.json()
    print(f"Found {len(chords_list)} chord history records.")
    if len(chords_list) > 0:
        latest = chords_list[0]
        print(f"Latest record: {latest['tab_name']} - Status: {latest['status']}")
        print(f"Latest record has {len(latest['chords'])} chords embedded.")
else:
    print(f"My-Chords Error: {response.text}")

os.remove("test.wav")
