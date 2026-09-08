from pydantic import BaseModel
from typing import List, Optional

class SearchRequest(BaseModel):
    job_target: str
    location: str
    max_results: int = 5

class CandidateResult(BaseModel):
    id: int
    name_or_snippet: str
    phone: Optional[str] = None
    job_target: str
    score: float
    whatsapp_link: Optional[str] = None
    status: str

    class Config:
        from_attributes = True

class SearchResponse(BaseModel):
    message: str
    searched: int
    qualified: int
    saved: int
    duplicates: int
    rejected: int
    candidates: List[CandidateResult]
