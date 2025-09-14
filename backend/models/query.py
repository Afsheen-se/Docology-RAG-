from pydantic import BaseModel
from typing import List, Optional

class QueryRequest(BaseModel):
    query: str
    document_ids: Optional[List[str]] = None

class QueryResponse(BaseModel):
    answer: str
    citations: List[dict]
