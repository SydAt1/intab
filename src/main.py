from db.setup import create_tables
from auth.user import register_user, login_user

# Create tables
create_tables()

# Test register & login
register_user("testuser", "test@example.com", "mypassword")
login_user("testuser", "mypassword")
