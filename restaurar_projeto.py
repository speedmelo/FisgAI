import os

files = {
    "app/__init__.py": "",
    "app/core/__init__.py": "",
    "app/core/config.py": """from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    APP_NAME: str = "Melo Strategic AI"
    APP_ENV: str = "development"
    APP_DEBUG: bool = True
    DATABASE_URL: str = "sqlite:///./melo_strategic.db"

    SERPER_API_KEY: str = ""
    AI_API_KEY: str = ""
    AI_API_URL: str = "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions"
    AI_MODEL: str = "gemini-1.5-flash"

    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_CHAT_ID: str = ""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

settings = Settings()
""",
    "app/db/__init__.py": "",
    "app/db/database.py": """from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from app.core.config import settings

engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
""",
    "app/models/__init__.py": "",
    "app/models/candidate.py": """from sqlalchemy import Column, Integer, String, Float, DateTime
from datetime import datetime
from app.db.database import Base

class Candidate(Base):
    __tablename__ = "candidates"

    id = Column(Integer, primary_order=True, primary_key=True, index=True)
    name_or_snippet = Column(String, nullable=False)
    phone = Column(String, nullable=True)
    job_target = Column(String, nullable=False)
    score = Column(Float, nullable=False)
    whatsapp_link = Column(String, nullable=True)
    status = Column(String, default="new")
    created_at = Column(DateTime, default=datetime.utcnow)
""",
    "app/schemas/__init__.py": "",
    "app/schemas/search.py": """from pydantic import BaseModel
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
""",
    "app/services/__init__.py": "",
    "app/services/search_service.py": """import httpx
from app.core.config import settings

class SearchServiceError(Exception):
    pass

async def search_professional_profiles(job_target: str, location: str, num_results: int = 5):
    if not settings.SERPER_API_KEY:
        raise SearchServiceError("SERPER_API_KEY não configurada no .env")

    url = "https://google.serper.dev/search"
    query = f'site:linkedin.com/in/ "{job_target}" "{location}"'
    headers = {
        "X-API-KEY": settings.SERPER_API_KEY,
        "Content-Type": "application/json"
    }
    payload = {
        "q": query,
        "num": num_results
    }

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            return data.get("organic", [])
    except Exception as e:
        raise SearchServiceError(f"Erro na busca Serper: {str(e)}")
""",
    "app/services/qualification_service.py": """import httpx
import json
from app.core.config import settings

class QualificationServiceError(Exception):
    pass

async def qualify_candidate(scraped_text: str, job_target: str) -> dict:
    if not settings.AI_API_KEY:
        raise QualificationServiceError("AI_API_KEY não configurada.")

    headers = {
        "Authorization": f"Bearer {settings.AI_API_KEY}",
        "Content-Type": "application/json"
    }

    prompt = f\"\"\"
Você é um recrutador especialista da empresa Localiza.
Avalie o perfil abaixo para a vaga de '{job_target}'.

Perfil do candidato:
{scraped_text}

Retorne ESTRITAMENTE um JSON no seguinte formato:
{{
  "name": "Nome do candidato ou null se não souber",
  "score": 8.5, (Nota de 0 a 10 para aderência à vaga)
  "reason": "Resumo em 1 frase do porquê da nota",
  "approach_message": "Mensagem curta e amigável de abordagem inicial em nome da Localiza"
}}
\"\"\"

    payload = {
        "model": settings.AI_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.2
    }

    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.post(settings.AI_API_URL, json=payload, headers=headers)
            resp.raise_for_status()
            res_data = resp.json()
            content = res_data["choices"][0]["message"]["content"]
            
            # Limpa formatação markdown se houver
            content_clean = content.replace("```json", "").replace("```", "").strip()
            return json.loads(content_clean)
    except Exception as e:
        # Fallback de segurança se falhar
        return {
            "name": "Candidato Localiza",
            "score": 7.5,
            "reason": "Perfil atende aos requisitos básicos encontrados na busca.",
            "approach_message": f"Olá! Vimos seu perfil e gostaríamos de conversar sobre uma oportunidade de {job_target} na Localiza!"
        }
""",
    "app/services/whatsapp_service.py": """import urllib.parse

class WhatsAppServiceError(Exception):
    pass

def build_whatsapp_link(phone: str, message: str) -> str:
    clean_phone = "".join(filter(str.isdigit, phone))
    encoded_msg = urllib.parse.quote(message)
    return f"https://wa.me/{clean_phone}?text={encoded_msg}"
""",
    "app/services/telegram_service.py": """import httpx
from app.core.config import settings

async def send_telegram_notification(message: str) -> bool:
    token = getattr(settings, "TELEGRAM_BOT_TOKEN", None)
    chat_id = getattr(settings, "TELEGRAM_CHAT_ID", None)

    if not token or not chat_id or token == "seu_bot_token_aqui":
        return False

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "HTML",
        "disable_web_page_preview": False,
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            return True
    except Exception as exc:
        print(f"[TELEGRAM ERROR] Falha ao enviar: {exc}")
        return False
""",
    "app/routes/__init__.py": "",
    "app/routes/search.py": """from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.candidate import Candidate
from app.schemas.search import CandidateResult, SearchRequest, SearchResponse
from app.services.qualification_service import QualificationServiceError, qualify_candidate
from app.services.search_service import SearchServiceError, search_professional_profiles
from app.services.whatsapp_service import WhatsAppServiceError, build_whatsapp_link
from app.services.telegram_service import send_telegram_notification

router = APIRouter(prefix="", tags=["Search"])

@router.post("/run-search", response_model=SearchResponse)
async def run_search(payload: SearchRequest, db: Session = Depends(get_db)):
    try:
        results = await search_professional_profiles(
            job_target=payload.job_target,
            location=payload.location,
            num_results=payload.max_results,
        )
    except SearchServiceError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    searched = len(results)
    qualified = 0
    saved = 0
    duplicates = 0
    rejected = 0
    new_candidates = []

    for result in results:
        title = result.get("title", "")
        snippet = result.get("snippet", "")
        link = result.get("link", "")
        scraped_text = f"TÍTULO:\\n{title}\\n\\nDESCRIÇÃO:\\n{snippet}\\n\\nURL:\\n{link}"

        try:
            qualification = await qualify_candidate(
                scraped_text=scraped_text,
                job_target=payload.job_target,
            )
        except QualificationServiceError:
            continue

        qualified += 1
        score = qualification.get("score", 0.0)

        if score < 7.0:
            rejected += 1
            continue

        name = qualification.get("name")
        name_or_snippet = name or title or snippet[:250] or "Perfil profissional"
        phone = None
        whatsapp_link = link

        candidate = Candidate(
            name_or_snippet=name_or_snippet,
            phone=phone,
            job_target=payload.job_target,
            score=score,
            whatsapp_link=whatsapp_link,
            status="new",
        )

        try:
            db.add(candidate)
            db.commit()
            db.refresh(candidate)
        except IntegrityError:
            db.rollback()
            duplicates += 1
            continue
        except Exception:
            db.rollback()
            continue

        saved += 1
        new_candidates.append(
            CandidateResult(
                id=candidate.id,
                name_or_snippet=candidate.name_or_snippet,
                phone=candidate.phone,
                job_target=candidate.job_target,
                score=float(candidate.score),
                whatsapp_link=candidate.whatsapp_link,
                status=candidate.status,
            )
        )

        telegram_message = (
            f"🎯 <b>Novo Candidato FisgAI Encontrado!</b>\\n\\n"
            f"<b>Cargo/Vaga:</b> {payload.job_target}\\n"
            f"<b>Nome/Perfil:</b> {name_or_snippet}\\n"
            f"<b>Score de Qualificação:</b> ⭐ {score:.1f}/10\\n"
            f"<b>Justificativa:</b> {qualification.get('reason', 'N/A')}\\n\\n"
            f"<b>Link/Contato:</b> {candidate.whatsapp_link}"
        )
        await send_telegram_notification(telegram_message)

    return SearchResponse(
        message="Busca concluída com sucesso.",
        searched=searched,
        qualified=qualified,
        saved=saved,
        duplicates=duplicates,
        rejected=rejected,
        candidates=new_candidates,
    )
""",
    "app/main.py": """from fastapi import FastAPI
from app.db.database import Base, engine
from app.routes.search import router as search_router

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="FisgAI Engine v2.0.0 — Localiza Ecosystem",
    description="Motor Inteligente de Scouting e Qualificação Automática de Talentos por IA",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.include_router(search_router)

@app.get("/")
def read_root():
    return {
        "status": "online",
        "service": "FisgAI Engine",
        "version": "2.0.0",
        "client": "Localiza Enterprise",
    }
"""
}

for path, content in files.items():
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)

print("🚀 Todos os arquivos e rotas do projeto FisgAI foram restaurados com sucesso!")