import requests
import uuid
import sys

# Constants
BASE_URL = "http://127.0.0.1:8000/api"

def run_test():
    username = f"testuser_{uuid.uuid4().hex[:6]}"
    email = f"{username}@example.com"
    password = "securepassword123"

    print(f"Starting Auth Integration Test for {username}")
    
    # 1. Register
    print("\n[1] Registering User...")
    try:
        reg_resp = requests.post(f"{BASE_URL}/register", json={
            "username": username,
            "email": email,
            "password": password
        })
        if reg_resp.status_code == 201:
            print("    ✅ Registration Successful")
        else:
            print(f"    ❌ Registration Failed: {reg_resp.text}")
            return False
    except Exception as e:
        print(f"    ❌ Connection Error: {e}")
        return False

    # 2. Login
    print("\n[2] Logging In...")
    login_resp = requests.post(f"{BASE_URL}/login", json={
        "username": username,
        "password": password
    })
    
    if login_resp.status_code != 200:
        print(f"    ❌ Login Failed: {login_resp.text}")
        return False

    data = login_resp.json()
    token = data.get("access_token")
    session_id = data.get("session_id")

    if not token or not session_id:
        print("    ❌ Login response missing token or session_id")
        return False

    print("    ✅ Login Successful")
    print(f"       Token: {token[:10]}...")
    print(f"       Session ID: {session_id}")

    # 3. Verify /me with Session ID
    print("\n[3] Verifying /me with Session ID...")
    headers = {
        "Authorization": f"Bearer {token}",
        "X-Session-Id": session_id
    }
    me_resp = requests.get(f"{BASE_URL}/me", headers=headers)
    
    if me_resp.status_code == 200:
        user_data = me_resp.json()
        if user_data.get("username") == username:
             print("    ✅ /me returned correct user data")
        else:
             print(f"    ❌ /me returned incorrect user: {user_data}")
             return False
    else:
        print(f"    ❌ /me failed: {me_resp.status_code} - {me_resp.text}")
        return False

    # 4. Logout
    print("\n[4] Logging Out...")
    logout_headers = {"X-Session-Id": session_id}
    logout_resp = requests.post(f"{BASE_URL}/logout", headers=logout_headers)
    
    if logout_resp.status_code == 200:
        print("    ✅ Logout Successful")
    else:
        print(f"    ❌ Logout Failed: {logout_resp.status_code} - {logout_resp.text}")
        return False
        
    print("\n✨ All tests passed successfully!")
    return True

if __name__ == "__main__":
    if run_test():
        sys.exit(0)
    else:
        sys.exit(1)
