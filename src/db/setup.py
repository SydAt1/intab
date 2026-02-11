from db.connection import engine
from db.models import Base

def create_tables():
    Base.metadata.create_all(engine)
    print("Tables created successfully!")

if __name__ == "__main__":
    create_tables()
