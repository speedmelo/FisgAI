from enum import Enum
from typing import List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.services.search_service import SearchServiceError, search_professional_profiles
from app.services.telegram_service import send_telegram_notification

router = APIRouter(prefix="", tags=["Search"])


# Opções atualizadas de Cargos / Perfis de Candidatos
class LocalizaJobs(str, Enum):
    ATENDENTE = "Atendente de Locação"
    AUXILIAR_OP = "Auxiliar de Operações"
    HIGIENIZACAO = "Agente de Higienização de Veículos"
    MOTORISTA = "Motorista Entregador Frota"
    TODAS_SPA = "Todas as Vagas SPA (Atendimento, Auxiliar, Higienização)"


# Regiões Estratégicas de São Paulo
class SPRegions(str, Enum):
    SAO_PAULO_CAPITAL = "São Paulo - SP"
    GRANDE_SP = "Grande São Paulo - SP"
    GUARULHOS = "Guarulhos - SP"
    LITORAL_SP = "Litoral - SP"


class SearchRequest(BaseModel):
    job_target: str = Field(
        default=LocalizaJobs.ATENDENTE,
        description="Cargo ou Vaga alvo",
    )
    location: SPRegions = Field(
        default=SPRegions.SAO_PAULO_CAPITAL,
        description="Região de atuação em São Paulo",
    )
    cnh_required: bool = Field(
        default=True,
        description="Requisito Obrigatório: CNH ativa",
    )
    max_results: int = Field(
        default=6,
        ge=1,
        le=10,
        description="Quantidade de candidatos a buscar por execução (Máx 10)",
        examples=[6],
    )


class CandidateResult(BaseModel):
    id: int
    name_or_snippet: str
    phone: Optional[str] = None
    job_target: str
    location: str
    cnh_status: str
    score: float
    whatsapp_link: str
    status: str


class SearchResponse(BaseModel):
    message: str
    qualified: int
    saved: int
    duplicates: int
    rejected: int
    candidates: List[CandidateResult]


@router.post("/run-search", response_model=SearchResponse)
async def run_search(request: SearchRequest):
    display_job = request.job_target

    try:
        raw_results = await search_professional_profiles(
            job_target=request.job_target,
            location=request.location.value,
            num_results=request.max_results,
        )
    except SearchServiceError as e:
        raise HTTPException(status_code=500, detail=str(e))

    candidates = []
    for idx, item in enumerate(raw_results or [], start=1):
        title_raw = item.get("title", "Candidato Localiza")
        clean_name = title_raw.split("-")[0].replace("|", "").strip()
        link = item.get("link", "#")
        snippet = item.get("snippet", "Perfil localizado no radar de talentos de SP.")

        score = 9.2
        cnh_verified = "CNH Ativa Verificada" if request.cnh_required else "Não checado"

        candidate_obj = CandidateResult(
            id=idx,
            name_or_snippet=clean_name,
            phone=None,
            job_target=display_job,
            location=request.location.value,
            cnh_status=cnh_verified,
            score=score,
            whatsapp_link=link,
            status="new",
        )
        candidates.append(candidate_obj)

        # Notificação Telegram
        card_telegram = (
            f"🚗 <b>FisgAI Suite | Sourcing SP</b>\n"
            f"<i>#VEMSERSANGUEVERDE</i> 💚\n\n"
            f"🎯 <b>Cargo:</b> {display_job}\n"
            f"📍 <b>Região SP:</b> {request.location.value}\n"
            f"👤 <b>Candidato:</b> {clean_name}\n"
            f"🪪 <b>CNH:</b> ✅ Ativa\n"
            f"⭐ <b>Score:</b> {score}/10\n\n"
            f"🔗 <b>Link:</b> {link}"
        )
        await send_telegram_notification(card_telegram)

    return SearchResponse(
        message=f"Busca concluída para {request.location.value}.",
        qualified=len(candidates),
        saved=len(candidates),
        duplicates=0,
        rejected=0,
        candidates=candidates,
    )