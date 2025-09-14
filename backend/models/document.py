from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class DocumentChunk(BaseModel):
    text: str
    metadata: dict

class Document(BaseModel):
    id: str
    filename: str
    pages: int
    size: int
    created_at: datetime
    chunks: List[DocumentChunk]

class DocumentResponse(BaseModel):
    id: str
    filename: str
    pages: int
    size: int
    created_at: datetime
