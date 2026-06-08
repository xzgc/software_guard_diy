from sqlalchemy import Column, String, Integer, BigInteger, Text, DateTime
from sqlalchemy.sql import func
from ..core.database import Base


class UploadSession(Base):
    __tablename__ = "upload_sessions"

    id = Column(String(36), primary_key=True)
    software_id = Column(Integer, nullable=False)
    file_name = Column(String(255), nullable=False)
    file_size = Column(BigInteger, nullable=False)
    file_hash = Column(String(64))
    chunk_size = Column(Integer, nullable=False)
    total_chunks = Column(Integer, nullable=False)
    uploaded_chunks = Column(Integer, default=0)
    status = Column(String(20), default="pending")
    uploader_id = Column(Integer, nullable=False)
    version = Column(String(50), nullable=False)
    release_notes = Column(Text)
    temp_dir = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
