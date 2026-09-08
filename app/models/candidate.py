from datetime import datetime
from sqlalchemy import Column, DateTime, Float, Integer, String
from app.db.database import Base


class Candidate(Base):
    __tablename__ = "candidates"

    id = Column(Integer, primary_key=True, index=True)
    name_or_snippet = Column(String, nullable=False)
    phone = Column(String, nullable=True)
    job_target = Column(String, nullable=False)
    score = Column(Float, nullable=False)
    whatsapp_link = Column(String, nullable=True)
    status = Column(String, default="new")
    created_at = Column(DateTime, default=datetime.utcnow)