import httpx
import time

BASE_URL = "http://127.0.0.1:8000"

def test_api():
    print("Waiting for server to start...")
    # Simple retry logic to wait for server
    for _ in range(5):
        try:
            httpx.get(BASE_URL)
            break
        except httpx.ConnectError:
            time.sleep(1)
    else:
        print("Server didn't start in time or is not reachable.")
        return

    # 1. Register
    print("\n[TEST] Registering user...")
    register_data = {
        "username": "api_user",
        "email": "api@example.com",
        "password": "apipassword"
    }
    response = httpx.post(f"{BASE_URL}/register", json=register_data)
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")

    # 2. Login
    print("\n[TEST] Logging in...")
    login_data = {
        "username": "api_user",
        "password": "apipassword"
    }
    response = httpx.post(f"{BASE_URL}/login", json=login_data)
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")

    # 3. Invalid Login
    print("\n[TEST] Invalid login...")
    invalid_data = {
        "username": "api_user",
        "password": "wrongpassword"
    }
    response = httpx.post(f"{BASE_URL}/login", json=invalid_data)
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")

if __name__ == "__main__":
    test_api()
