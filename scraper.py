
from __future__ import annotations

import logging
import time
from typing import Any
from urllib.parse import urlparse

import httpx
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

from app.core.config import settings

logger = logging.getLogger("fisgai_scraper")

SERPER_ENDPOINT = "https://google.serper.dev/search"
GOOGLE_CSE_ENDPOINT = "https://www.googleapis.com/customsearch/v1"


class SearchConfigurationError(Exception):
    """Provedor de busca não configurado."""


class SearchProviderError(Exception):
    """Erro ao consultar o provedor de busca."""


class SearchClient:
    def __init__(self) -> None:
        self.serper_key = settings.SERPER_API_KEY
        self.google_api_key = getattr(settings, "GOOGLE_API_KEY", "")
        self.google_cse_id = getattr(settings, "GOOGLE_CSE_ID", "")

        if not self.serper_key and not (
            self.google_api_key and self.google_cse_id
        ):
            raise SearchConfigurationError(
                "Configure SERPER_API_KEY ou GOOGLE_API_KEY e GOOGLE_CSE_ID."
            )

        self.client = httpx.Client(timeout=20.0)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=5),
        retry=retry_if_exception_type(
            (httpx.HTTPStatusError, httpx.RequestError)
        ),
        reraise=True,
    )
    def search(
        self, query: str, num: int = 10
    ) -> list[dict[str, Any]]:
        num = min(max(int(num), 1), 10)

        if self.serper_key:
            response = self.client.post(
                SERPER_ENDPOINT,
                headers={
                    "X-API-KEY": self.serper_key,
                    "Content-Type": "application/json",
                },
                json={
                    "q": query,
                    "num": num,
                    "gl": "br",
                    "hl": "pt-br",
                },
            )
        else:
            response = self.client.get(
                GOOGLE_CSE_ENDPOINT,
                params={
                    "key": self.google_api_key,
                    "cx": self.google_cse_id,
                    "q": query,
                    "num": num,
                    "gl": "br",
                    "hl": "pt-br",
                },
            )

        response.raise_for_status()
        data = response.json()

        if self.serper_key:
            return data.get("organic", [])

        return data.get("items", [])

    def close(self) -> None:
        self.client.close()


def scrape_job_seekers(
    max_results_per_query: int = 5,
    max_queries: int = 3,
    delay_between_queries: float = 0.5,
    job_target: str = "Atendimento ao Cliente",
    location: str = "Brasil",
) -> list[dict[str, Any]]:
    """Busca referências públicas para revisão humana.

    Encontrar um perfil ou uma publicação não comprova que a pessoa
    esteja procurando emprego atualmente.
    """
    job_target = job_target.strip()
    location = location.strip()

    if not job_target or not location:
        raise ValueError("Informe o cargo e a localização.")

    if max_queries < 1 or max_results_per_query < 1:
        raise ValueError("Os limites da busca devem ser maiores que zero.")

    # Consultas alternativas: perfis públicos e publicações sobre emprego.
    all_queries = [
        (
            f'site:linkedin.com/in/ "{job_target}" "{location}" '
            f'(currículo OR experiência OR profissional)'
        ),
        (
            f'"{job_target}" "{location}" '
            f'("estou procurando emprego" OR "em busca de oportunidade")'
        ),
        (
            f'"{job_target}" "{location}" '
            f'("disponível para trabalhar" OR "busco uma oportunidade")'
        ),
        (
            f'site:linkedin.com/posts/ "{job_target}" "{location}" '
            f'(vaga OR emprego OR oportunidade)'
        ),
        (
            f'"{job_target}" "{location}" '
            f'("envie seu currículo" OR "candidate-se")'
        ),
    ]
    queries = all_queries[:min(max_queries, len(all_queries))]

    client = SearchClient()
    results: list[dict[str, Any]] = []
    seen_links: set[str] = set()

    try:
        for index, query in enumerate(queries):
            try:
                items = client.search(
                    query,
                    num=min(max_results_per_query, 10),
                )
            except (httpx.HTTPStatusError, httpx.RequestError) as exc:
                logger.exception("Falha ao consultar o provedor de busca.")
                raise SearchProviderError(
                    "A consulta ao provedor de busca falhou."
                ) from exc

            for item in items:
                title = str(item.get("title") or "").strip()
                snippet = str(item.get("snippet") or "").strip()
                link = str(item.get("link") or "").strip()

                if not title or not link.startswith(("https://", "http://")):
                    continue

                parsed = urlparse(link)
                if not parsed.hostname:
                    continue

                normalized_link = link.rstrip("/")
                if normalized_link in seen_links:
                    continue

                seen_links.add(normalized_link)

                results.append({
                    "title": title,
                    "snippet": snippet,
                    "link": link,
                    "source": parsed.hostname.lower(),
                    "job_target": job_target,
                    "location": location,
                    "review_required": True,
                    "candidate_intent_verified": False,
                })

            if index < len(queries) - 1 and delay_between_queries > 0:
                time.sleep(delay_between_queries)

    finally:
        client.close()

    logger.info(
        "Busca concluída: %d referência(s); cargo=%s; localização=%s.",
        len(results),
        job_target,
        location,
    )
    return results
