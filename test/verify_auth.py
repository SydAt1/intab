import requests
import uuid

BASE_URL = "http://127.0.0.1:8000"

def verify_auth():
    username = f"user_{uuid.uuid4().hex[:8]}"
    email = f"{username}@example.com"
    password = "testpassword123"

    print(f"Testing with user: {username}")

    # 1. Register
    print("1. Registering user...")
    resp = requests.post(f"{BASE_URL}/register", json={
        "username": username,
        "email": email,
        "password": password
    })
    if resp.status_code == 201:
        print("   Registration successful")
    else:
        print(f"   Registration failed: {resp.text}")
        return

    # 2. Login
    print("2. Logging in...")
    resp = requests.post(f"{BASE_URL}/login", json={
        "username": username,
        "password": password
    })
    
    if resp.status_code == 200:
        data = resp.json()
        access_token = data.get("access_token")
        session_id = data.get("session_id")
        
        if access_token and session_id:
            print(f"   Login successful.")
            print(f"   Access Token: {access_token[:20]}...")
            print(f"   Session ID: {session_id}")
        else:
            print("   Login failed: Missing token or session ID")
            print(f"   Response: {data}")
            return
    else:
        print(f"   Login failed: {resp.text}")
        return

    # 3. Verify Token (/me)
    print("3. Verifying token...")
    headers = {"Authorization": f"Bearer {access_token}"}
    resp = requests.get(f"{BASE_URL}/me", headers=headers)
    
    if resp.status_code == 200:
        user_data = resp.json()
        if user_data["username"] == username:
            print("   Token verification successful. correct user returned.")
        else:
            print(f"   Token verification failed: User mismatch. Got {user_data['username']}")
    else:
        print(f"   Token verification failed: {resp.status_code} - {resp.text}")

if __name__ == "__main__":
    try:
        verify_auth()
    except requests.exceptions.ConnectionError:
        print("Error: Could not connect to server. Make sure it is running on port 8000.")
