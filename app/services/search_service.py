
import logging

from starlette.concurrency import run_in_threadpool

from scraper import (
    SearchConfigurationError,
    SearchProviderError,
    scrape_job_seekers,
)
from app.services.qualification_service import (
    QualificationServiceError,
    qualify_candidate,
)

logger = logging.getLogger("FisgAI.SearchService")


class SearchServiceError(Exception):
    """Erro durante a busca de perfis públicos."""


async def search_professional_profiles(
    job_target: str,
    location: str,
    num_results: int = 10,
) -> list[dict]:
    if not job_target or not job_target.strip():
        raise SearchServiceError("Informe o cargo desejado.")

    if not location or not location.strip():
        raise SearchServiceError("Informe a localização.")

    try:
        safe_num = min(max(int(num_results), 1), 10)
    except (TypeError, ValueError) as exc:
        raise SearchServiceError(
            "A quantidade de resultados deve ser um número inteiro."
        ) from exc

    job_target = job_target.strip()
    location = location.strip()

    try:
        results = await run_in_threadpool(
            scrape_job_seekers,
            job_target=job_target,
            location=location,
            max_results_per_query=min(safe_num, 5),
            max_queries=5,
            delay_between_queries=0.5,
        )
    except (SearchConfigurationError, SearchProviderError) as exc:
        logger.error("Falha na configuração ou consulta de busca: %s", exc)
        raise SearchServiceError(str(exc)) from exc
    except Exception as exc:
        logger.exception("Falha inesperada durante a busca.")
        raise SearchServiceError(
            "Ocorreu um erro inesperado durante a busca."
        ) from exc

    candidates = []
    seen_links = set()

    for result in results or []:
        title = str(result.get("title") or "").strip()
        snippet = str(result.get("snippet") or "").strip()
        link = str(result.get("link") or "").strip()
        source = str(result.get("source") or "").strip()

        if not title or not link.startswith(("https://", "http://")):
            continue

        normalized_link = link.rstrip("/")
        if normalized_link in seen_links:
            continue

        seen_links.add(normalized_link)

        candidate = {
            "title": title,
            "snippet": snippet,
            "link": link,
            "source": source,
            "job_target": job_target,
            "location": location,
            "score": None,
            "phone": None,
            "status": "pending_review",
            "review_required": True,
            "candidate_intent_verified": False,
            "qualification": None,
            "qualification_status": "not_evaluated",
        }

        # A IA analisa somente as informações públicas retornadas
        # pela busca. Não acessamos nem presumimos dados privados.
        profile_text = (
            f"Título do resultado: {title}\n"
            f"Trecho público da busca: {snippet}\n"
            f"Fonte: {source}\n"
            f"URL pública: {link}"
        )

        try:
            qualification = await qualify_candidate(
                scraped_text=profile_text,
                job_target=job_target,
            )

            candidate["qualification"] = qualification
            candidate["score"] = qualification.get("score")
            candidate["qualification_status"] = "evaluated"

        except QualificationServiceError:
            logger.warning(
                "Não foi possível qualificar o resultado: %s",
                link,
            )
            candidate["qualification_status"] = "failed"

        candidates.append(candidate)

        if len(candidates) >= safe_num:
            break

    logger.info(
        "Busca concluída: %d referência(s) para cargo=%s, localização=%s.",
        len(candidates),
        job_target,
        location,
    )

    return candidates
