import sys
import os
from datetime import datetime, timedelta

# Adjust path to import from src
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "Users", "sydatsin", "Islington College", "FYP_project")))

from src.db.connection import SessionLocal
from src.db.models import User
from src.db.audio_model import AudioFile
from src.db.tablature_model import Tablature
from src.db.chord_model import Chord
from src.auth.password_utils import hash_password, verify_password
from src.util.email import send_reset_email
import secrets

def test_flow():
    db = SessionLocal()
    email = "sydatsin4aiml@gmail.com"
    username = "test_user_for_verification"
    password = "InitialPassword123!"
    new_password = "ModifiedPassword456!"

    try:
        # 1. Clean up existing test user if any
        existing_user = db.query(User).filter(User.username == username).first()
        if existing_user:
            db.delete(existing_user)
            db.commit()
            print(f"Cleaned up existing user: {username}")

        # 2. Register test user
        print(f"Registering user: {username} with email: {email}")
        new_user = User(
            username=username,
            email=email,
            password_hash=hash_password(password)
        )
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        print("User registered successfully.")

        # 3. Simulate forgot password request
        print("Simulating forgot password request...")
        token = secrets.token_urlsafe(32)
        new_user.reset_token = token
        new_user.reset_token_expiry = datetime.utcnow() + timedelta(hours=1)
        db.commit()
        print(f"Generated reset token: {token[:10]}...")

        # 4. Test email sending
        print(f"Attempting to send reset email to {email}...")
        sent = send_reset_email(email, token)
        if sent:
            print("Email sent successfully!")
        else:
            print("Failed to send email. Check SMTP settings in .env")

        # 5. Simulate password reset using the token
        print("Simulating password reset with token...")
        reset_user = db.query(User).filter(
            User.reset_token == token,
            User.reset_token_expiry > datetime.utcnow()
        ).first()

        if reset_user:
            reset_user.password_hash = hash_password(new_password)
            reset_user.reset_token = None
            reset_user.reset_token_expiry = None
            db.commit()
            print("Password reset successfully in DB.")
        else:
            print("Error: Could not find user with valid token.")
            return

        # 6. Verify new password
        db.refresh(new_user)
        if verify_password(new_password, new_user.password_hash):
            print("VERIFICATION SUCCESS: New password is valid!")
        else:
            print("VERIFICATION FAILURE: New password is not valid.")

    except Exception as e:
        print(f"An error occurred during testing: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    test_flow()
