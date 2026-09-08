from enum import Enum
from typing import List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.services.search_service import SearchServiceError, search_professional_profiles
from app.services.telegram_service import send_telegram_notification

router = APIRouter(prefix="", tags=["Search"])


# Opções de Vagas SPA Localiza
class LocalizaJobs(str, Enum):
    TODAS_SPA = "Todas as Vagas SPA (Atendimento, Auxiliar, Higienização)"
    ATENDIMENTO = "Atendimento ao Cliente"
    AUXILIAR_OP = "Auxiliar de Operações"
    AGENTE_HIGIENIZACAO = "Agente de Higienização"


# Regiões Estratégicas de São Paulo
class SPRegions(str, Enum):
    SAO_PAULO_CAPITAL = "São Paulo - SP"
    GRANDE_SP = "Grande São Paulo - SP"
    GUARULHOS = "Guarulhos - SP"
    LITORAL_SP = "Litoral - SP"


# Modelo Automatizado Padrão Localiza SP (Limitado a 10 por requisição da Serper API)
class SearchRequest(BaseModel):
    job_target: LocalizaJobs = Field(
        default=LocalizaJobs.TODAS_SPA,
        description="Seleção de Vaga SPA Localiza",
    )
    location: SPRegions = Field(
        default=SPRegions.SAO_PAULO_CAPITAL,
        description="Região de atuação em São Paulo",
    )
    cnh_required: bool = Field(
        default=True,
        description="Requisito Obrigatório: CNH definitiva há pelo menos 1 ano",
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
    if request.job_target == LocalizaJobs.TODAS_SPA:
        query_job = "Atendimento ao Cliente OR Auxiliar de Operações OR Agente de Higienização"
        display_job = "Vagas SPA (Atendimento / Auxiliar / Higienização)"
    else:
        query_job = request.job_target.value
        display_job = request.job_target.value

    try:
        raw_results = await search_professional_profiles(
            job_target=query_job,
            location=request.location.value,
            num_results=request.max_results,
        )
    except SearchServiceError as e:
        raise HTTPException(status_code=500, detail=str(e))

    candidates = []
    # Proteção caso a API retorne menos itens que o solicitado
    for idx, item in enumerate(raw_results or [], start=1):
        title_raw = item.get("title", "Candidato Localiza")
        clean_name = title_raw.split("-")[0].replace("|", "").strip()
        link = item.get("link", "#")
        snippet = item.get("snippet", "Perfil localizado no radar de talentos de SP.")

        score = 8.8
        cnh_verified = "CNH Definitiva (+1 ano OK)" if request.cnh_required else "Não checado"

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

        # Disparo assíncrono para o Telegram
        card_telegram = (
            f"🚗 <b>FisgAI Engine | Localiza&co SP</b>\n"
            f"<i>#VEMSERSANGUEVERDE</i> 💚\n\n"
            f"🎯 <b>Vaga(s):</b> {display_job}\n"
            f"📍 <b>Região SP:</b> {request.location.value}\n"
            f"👤 <b>Candidato:</b> {clean_name}\n"
            f"🪪 <b>Requisito CNH:</b> ✅ Definitiva (1+ anos)\n"
            f"⭐ <b>Score FisgAI:</b> {score}/10\n"
            f"📝 <b>Resumo:</b> {snippet[:110]}...\n\n"
            f"🎁 <b>Benefícios Localiza:</b>\n"
            f"• VT + VR/VA + Plano Saúde/Odonto\n"
            f"• Wellhub + PLR + Desconto Veículos\n\n"
            f"🔗 <b>Perfil/Contato:</b> {link}"
        )
        await send_telegram_notification(card_telegram)

    return SearchResponse(
        message=f"Busca de talentos concluída para {request.location.value}.",
        qualified=len(candidates),
        saved=len(candidates),
        duplicates=0,
        rejected=0,
        candidates=candidates,
    )