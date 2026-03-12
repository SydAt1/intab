from src.db.connection import engine
from src.db.models import Base
from src.db.audio_model import AudioFile
from src.db.tablature_model import Tablature
from src.db.chord_model import Chord

def create_tables():
    Base.metadata.create_all(engine)
    print("Tables created successfully!")

if __name__ == "__main__":
    create_tables()
