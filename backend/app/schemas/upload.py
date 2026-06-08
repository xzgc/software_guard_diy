from pydantic import BaseModel, Field
from typing import Optional


class UploadInitRequest(BaseModel):
    software_id: int
    file_name: str = Field(..., min_length=1, max_length=255)
    file_size: int = Field(..., gt=0)
    file_hash: str = Field(..., min_length=64, max_length=64)
    total_chunks: int = Field(..., ge=1)
    chunk_size: int = Field(..., gt=0)
    version: str = Field(..., min_length=1)
    release_notes: Optional[str] = None


class UploadInitResponse(BaseModel):
    session_id: str
    chunk_size: int
    total_chunks: int


class UploadChunkResponse(BaseModel):
    session_id: str
    chunk_index: int
    uploaded_chunks: int
    total_chunks: int


class UploadCompleteResponse(BaseModel):
    session_id: str
    version_id: int
    file_name: str
    file_size: int
    file_hash: str
