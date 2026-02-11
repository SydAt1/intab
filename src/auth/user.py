from db.connection import SessionLocal
from db.models import User
from .password_utils import hash_password, verify_password

def register_user(username, email, password):
    session = SessionLocal()
    user = User(username=username, email=email, password_hash=hash_password(password))
    session.add(user)
    session.commit()
    session.close()
    print(f"User {username} registered successfully!")

def login_user(username, password):
    session = SessionLocal()
    user = session.query(User).filter_by(username=username).first()
    session.close()
    if user and verify_password(password, user.password_hash):
        print("Login successful!")
        return True
    print("Login failed!")
    return False
