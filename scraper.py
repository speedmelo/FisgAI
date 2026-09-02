"""
scraper.py
Módulo de busca de postagens públicas e perfis no Google via Serper API
(ou Google Custom Search) com Google Dorking dinâmico, extração de telefones
celulares brasileiros e tratamento robusto de erros/retries/cota.
"""

from __future__ import annotations

import os
import re
import time
import logging
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, asdict

import httpx
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
)

# ---------------------------------------------------------------------------
# Configuração de logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger("fisgai_scraper")

# ---------------------------------------------------------------------------
# Constantes e configuração
# ---------------------------------------------------------------------------
SERPER_ENDPOINT = "https://google.serper.dev/search"
GOOGLE_CSE_ENDPOINT = "https://www.googleapis.com/customsearch/v1"

TARGET_AREAS = [
    "Atendimento ao Cliente",
    "Auxiliar de Operações",
    "Agente de Higienização",
]

INTENT_TERMS = [
    "procuro vaga",
    "busco emprego",
    "disponível para",
    "à procura de vaga",
    "quero trabalhar",
    "aberto a oportunidades",
]

PRIORITY_SITES = [
    "linkedin.com/posts",
    "linkedin.com/in",
    "facebook.com",
    "instagram.com",
    "twitter.com",
    "x.com",
]

PHONE_REGEX = re.compile(
    r"""
    (?:
        (?:\+?55[\s\-]?)?               # +55 opcional
        (?:\(?\d{2}\)?[\s\-]?)           # DDD (11) ou 11
        (?:9[\s\-]?\d{4}[\s\-]?\d{4})    # 9XXXX-XXXX (celular)
    )
    |
    (?:
        (?:\+?55[\s\-]?)?
        (?:9[\s\-]?\d{4}[\s\-]?\d{4})    # sem DDD
    )
    """,
    re.VERBOSE | re.IGNORECASE,
)


@dataclass
class SearchResult:
    title: str
    snippet: str
    link: str
    extracted_phone: Optional[str]
    source: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Utilitários
# ---------------------------------------------------------------------------
def clean_phone(raw: str) -> str:
    digits = re.sub(r"\D", "", raw)
    if len(digits) == 11 and not digits.startswith("9"):
        return digits
    if len(digits) == 13 and digits.startswith("55"):
        return digits
    if len(digits) == 11:
        return digits
    return digits


def extract_phones(text: str) -> Optional[str]:
    if not text:
        return None
    matches = PHONE_REGEX.findall(text)
    for match in matches:
        cleaned = clean_phone(match)
        if len(cleaned) in (11, 13) and cleaned[-9] == "9":
            return cleaned
    return None


def build_dork_queries(
    areas: List[str] = TARGET_AREAS,
    intent_terms: List[str] = INTENT_TERMS,
    sites: List[str] = PRIORITY_SITES,
    max_queries: int = 12,
) -> List[str]:
    queries: List[str] = []

    for site in sites:
        for area in areas:
            for intent in intent_terms[:2]:
                q = f'site:{site} "{intent}" "{area}"'
                queries.append(q)
                if len(queries) >= max_queries:
                    return queries

    for area in areas:
        queries.append(f'"{intent_terms[0]}" "{area}" Brasil')
        if len(queries) >= max_queries:
            break

    return queries[:max_queries]


# ---------------------------------------------------------------------------
# Cliente de busca
# ---------------------------------------------------------------------------
class SearchClient:
    def __init__(self) -> None:
        self.serper_key = os.getenv("SERPER_API_KEY")
        self.google_api_key = os.getenv("GOOGLE_API_KEY")
        self.google_cse_id = os.getenv("GOOGLE_CSE_ID")

        if not self.serper_key and not (self.google_api_key and self.google_cse_id):
            logger.warning("Chaves de API de busca não encontradas no .env!")

        self.use_serper = bool(self.serper_key)
        self.client = httpx.Client(timeout=30.0)

    def _serper_search(self, query: str, num: int = 10) -> List[Dict[str, Any]]:
        headers = {
            "X-API-KEY": self.serper_key,
            "Content-Type": "application/json",
        }
        payload = {
            "q": query,
            "num": num,
            "gl": "br",
            "hl": "pt-br",
        }
        response = self.client.post(SERPER_ENDPOINT, headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()
        return data.get("organic", [])

    def _google_cse_search(self, query: str, num: int = 10) -> List[Dict[str, Any]]:
        params = {
            "key": self.google_api_key,
            "cx": self.google_cse_id,
            "q": query,
            "num": min(num, 10),
            "gl": "br",
            "hl": "pt-br",
        }
        response = self.client.get(GOOGLE_CSE_ENDPOINT, params=params)
        response.raise_for_status()
        data = response.json()
        return data.get("items", [])

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.HTTPStatusError, httpx.RequestError)),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )
    def search(self, query: str, num: int = 10) -> List[Dict[str, Any]]:
        try:
            if self.use_serper:
                return self._serper_search(query, num)
            elif self.google_api_key and self.google_cse_id:
                return self._google_cse_search(query, num)
            else:
                logger.error("Nenhum provedor de busca configurado.")
                return []
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 429:
                logger.warning("Quota excedida (429). Aguardando...")
                time.sleep(3)
            raise

    def close(self) -> None:
        self.client.close()


# ---------------------------------------------------------------------------
# Função principal importada pelo main.py
# ---------------------------------------------------------------------------
def scrape_job_seekers(
    max_results_per_query: int = 5,
    max_queries: int = 5,
    delay_between_queries: float = 1.0,
) -> List[Dict[str, Any]]:
    """
    Executa o pipeline completo de mineração de candidatos.
    """
    client = SearchClient()
    results: List[SearchResult] = []
    seen_links: set[str] = set()

    queries = build_dork_queries(max_queries=max_queries)

    try:
        for idx, query in enumerate(queries, start=1):
            try:
                raw_items = client.search(query, num=max_results_per_query)
            except Exception as exc:
                logger.error("Falha na query '%s': %s", query, exc)
                continue

            for item in raw_items:
                title = item.get("title", "")
                snippet = item.get("snippet", "")
                link = item.get("link", "")

                if not link or link in seen_links:
                    continue
                seen_links.add(link)

                source = link.split("/")[2] if "://" in link else "unknown"
                phone = extract_phones(f"{title} {snippet}")

                results.append(
                    SearchResult(
                        title=title.strip(),
                        snippet=snippet.strip(),
                        link=link,
                        extracted_phone=phone,
                        source=source,
                    )
                )

            if idx < len(queries):
                time.sleep(delay_between_queries)

    finally:
        client.close()

    return [r.to_dict() for r in results]


if __name__ == "__main__":
    import json
    data = scrape_job_seekers(max_results_per_query=2, max_queries=2)
    print(json.dumps(data, ensure_ascii=False, indent=2))