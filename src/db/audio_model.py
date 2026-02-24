from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, BigInteger
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
from src.db.models import Base

class AudioFile(Base):
    __tablename__ = "audio_files"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    original_filename = Column(String(255), nullable=False)
    storage_key = Column(String(500), nullable=False)
    file_size_bytes = Column(BigInteger, nullable=False)
    tab_name = Column(String(255), nullable=True)
    status = Column(String(50), default="pending", nullable=False)
    uploaded_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    user = relationship("User", back_populates="audio_files")
    tablature = relationship("Tablature", back_populates="audio_file", uselist=False)
