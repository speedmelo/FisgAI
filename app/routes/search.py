
import logging
from typing import List, Optional, Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.services.search_service import (
    SearchServiceError,
    search_professional_profiles,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Search"])


class SearchRequest(BaseModel):
    job_target: str = Field(
        ..., min_length=1, description="Vaga desejada"
    )
    location: str = Field(
        ..., min_length=1, description="Região da busca"
    )
    cnh_required: Optional[bool] = Field(
        default=True,
        description="Indica se a vaga exige CNH; não comprova esse requisito",
    )
    max_results: int = Field(default=10, ge=1, le=10)


class CandidateResult(BaseModel):
    # Identificador temporário desta resposta, não é ID do banco.
    id: int
    name_or_snippet: str
    profile_url: str
    phone: Optional[str] = None
    job_target: str
    location: str
    cnh_status: Any = "não confirmado"
    score: Optional[float] = None
    whatsapp_link: Optional[str] = None
    status: str = "pending_review"
    review_required: bool = True
    candidate_intent_verified: bool = False
    qualification_status: str = "not_evaluated"


class SearchResponse(BaseModel):
    message: str
    qualified: int
    saved: int
    duplicates: int
    rejected: int
    candidates: List[CandidateResult]


@router.post("/run-search", response_model=SearchResponse)
async def run_search(request: SearchRequest):
    job_target = request.job_target.strip()
    location = request.location.strip()

    if not job_target or not location:
        raise HTTPException(
            status_code=422,
            detail="Informe a vaga e a localização.",
        )

    try:
        raw_results = await search_professional_profiles(
            job_target=job_target,
            location=location,
            num_results=request.max_results,
        )
    except SearchServiceError as exc:
        logger.warning("Falha na busca de perfis: %s", exc)
        raise HTTPException(
            status_code=502,
            detail=(
                "Não foi possível concluir a busca. "
                "Verifique a configuração do provedor."
            ),
        ) from exc
    except Exception as exc:
        logger.exception("Erro inesperado em /run-search")
        raise HTTPException(
            status_code=500,
            detail="Erro interno durante a pesquisa.",
        ) from exc

    candidates = []

    for idx, item in enumerate(raw_results or [], start=1):
        title = str(item.get("title") or "").strip()
        profile_url = str(item.get("link") or "").strip()

        if not title or not profile_url.startswith(("https://", "http://")):
            continue

        qualification = item.get("qualification") or {}
        requirements = qualification.get("requirements") or {}

        cnh_status = requirements.get(
            "cnh_definitiva_1_ano",
            "não confirmado",
        )

        score = qualification.get("score")
        if not isinstance(score, (int, float)) or isinstance(score, bool):
            score = None
        else:
            score = max(0, min(10, float(score)))

        candidates.append(
            CandidateResult(
                id=idx,
                name_or_snippet=title,
                profile_url=profile_url,
                phone=None,
                job_target=job_target,
                location=location,
                cnh_status=cnh_status,
                score=score,
                whatsapp_link=None,
                status="pending_review",
                review_required=True,
                candidate_intent_verified=False,
                qualification_status=item.get(
                    "qualification_status",
                    "not_evaluated",
                ),
            )
        )

    return SearchResponse(
        message=(
            f"{len(candidates)} referência(s) pública(s) encontrada(s). "
            "Resultados preliminares; exigem revisão humana. "
            "Nenhum candidato foi salvo no banco ou contatado."
        ),
        qualified=0,
        saved=0,
        duplicates=0,
        rejected=0,
        candidates=candidates,
    )
