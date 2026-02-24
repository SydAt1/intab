from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
from src.db.models import Base

class Tablature(Base):
    __tablename__ = "tablatures"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    audio_file_id = Column(String, ForeignKey("audio_files.id"), nullable=False, unique=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    tab_content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    audio_file = relationship("AudioFile", back_populates="tablature")
