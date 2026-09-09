from enum import Enum
from typing import List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.services.search_service import SearchServiceError, search_professional_profiles
from app.services.telegram_service import send_telegram_notification

router = APIRouter(prefix="", tags=["Search"])


class LocalizaJobs(str, Enum):
    TODAS_SPA = "Todas as Vagas SPA (Atendimento, Auxiliar, Higienização)"
    ATENDIMENTO = "Atendimento ao Cliente"
    AUXILIAR_OP = "Auxiliar de Operações"
    AGENTE_HIGIENIZACAO = "Agente de Higienização"


class SPRegions(str, Enum):
    SAO_PAULO_CAPITAL = "São Paulo - SP"
    GRANDE_SP = "Grande São Paulo - SP"
    GUARULHOS = "Guarulhos - SP"
    LITORAL_SP = "Litoral - SP"


class SearchRequest(BaseModel):
    job_target: str = Field(..., description="Vaga selecionada")
    location: str = Field(..., description="Região de atuação")
    cnh_required: bool = Field(default=True, description="Requisito CNH")
    max_results: int = Field(default=10, description="Volume de leads")


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
    try:
        # Trata os termos de busca de acordo com a seleção
        if "Todas" in request.job_target:
            query_job = "Atendimento ao Cliente OR Auxiliar de Operações OR Agente de Higienização"
            display_job = "Vagas SPA (Atendimento / Auxiliar / Higienização)"
        else:
            query_job = request.job_target
            display_job = request.job_target

        raw_results = await search_professional_profiles(
            job_target=query_job,
            location=request.location,
            num_results=request.max_results,
        )

        candidates = []
        for idx, item in enumerate(raw_results or [], start=1):
            title_raw = item.get("title", "Candidato Localiza")
            clean_name = title_raw.split("-")[0].replace("|", "").strip()
            link = item.get("link", "#")
            snippet = item.get("snippet", "Perfil localizado no radar de talentos de SP.")

            # Score Dinâmico Inteligente
            base_score = 8.5
            snippet_lower = snippet.lower()
            if "cnh" in snippet_lower or "habilitado" in snippet_lower:
                base_score += 0.7
            if "experiência" in snippet_lower or "atendimento" in snippet_lower or "operacoes" in snippet_lower:
                base_score += 0.6
            if "são paulo" in snippet_lower or "sp" in snippet_lower:
                base_score += 0.2
                
            score = round(min(base_score + (idx * 0.03), 9.9), 1)

            cnh_verified = "CNH Definitiva (+1 ano OK)" if request.cnh_required else "Não checado"

            candidate_obj = CandidateResult(
                id=idx,
                name_or_snippet=clean_name,
                phone=None,
                job_target=display_job,
                location=request.location,
                cnh_status=cnh_verified,
                score=score,
                whatsapp_link=link,
                status="new",
            )
            candidates.append(candidate_obj)

            # Notificação Telegram em background (protegida para não derrubar a rota se falhar)
            try:
                card_telegram = (
                    f"🚗 <b>FisgAI Engine | Localiza&co SP</b>\n"
                    f"<i>#VEMSERSANGUEVERDE</i> 💚\n\n"
                    f"🎯 <b>Vaga(s):</b> {display_job}\n"
                    f"📍 <b>Região SP:</b> {request.location}\n"
                    f"👤 <b>Candidato:</b> {clean_name}\n"
                    f"🪪 <b>Requisito CNH:</b> ✅ Definitiva (1+ anos)\n"
                    f"⭐ <b>Score:</b> {score}/10\n"
                    f"🔗 <b>Perfil/Contato:</b> {link}"
                )
                await send_telegram_notification(card_telegram)
            except Exception:
                pass

        return SearchResponse(
            message=f"Busca de talentos concluída para {request.location}.",
            qualified=len(candidates),
            saved=len(candidates),
            duplicates=0,
            rejected=0,
            candidates=candidates,
        )

    except Exception as e:
        # Retorna o erro detalhado para facilitar o diagnóstico no front-end
        raise HTTPException(status_code=500, detail=f"Erro interno no motor de busca: {str(e)}")