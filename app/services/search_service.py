import logging
import random
from typing import List, Dict, Any
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from app.core.config import settings

logger = logging.getLogger("FisgAI.SearchService")


class SearchServiceError(Exception):
    """Exceção customizada para erros no serviço de busca."""
    pass


class SearchService:
    """Serviço de Sourcing Ativo especializado em varredura de pessoas reais na web aberta."""

    GOOGLE_SEARCH_URL = "https://google.serper.dev/search"
    
    # Termos de rotação para forçar indexação de perfis orgânicos e currículos reais
    KEYWORD_ROTATION_POOL = [
        "currículo", "experiência profissional", "resumo profissional", 
        "trajetória", "portfólio", "sobre mim", "histórico profissional"
    ]
    
    # Domínios corporativos e portais fechados a serem excluídos para focar em pessoas físicas
    EXCLUDED_DOMAINS = [
        "gupy.io", "vagas.com.br", "linkedin.com", 
        "indeed.com", "catho.com.br", "infojobs.com.br"
    ]

    @classmethod
    def _build_advanced_query(cls, job_target: str, location: str) -> str:
        """Constrói a query booleana avançada com exclusão de portais e rotação de termos."""
        random_keyword = random.choice(cls.KEYWORD_ROTATION_POOL)
        exclusions = " ".join([f"-site:{domain}" for domain in cls.EXCLUDED_DOMAINS])
        
        query = (
            f'("{job_target}") '
            f'("{location}") '
            f'("CNH" OR "Habilitado" OR "Motorista" OR "Categoria B") '
            f'("{random_keyword}") '
            f'{exclusions}'
        )
        return query

    @classmethod
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.HTTPError, httpx.TimeoutException)),
        reraise=True
    )
    async def _execute_request(cls, payload: Dict[str, Any], headers: Dict[str, str]) -> Dict[str, Any]:
        """Executa a requisição HTTP com política de retry e backoff exponencial."""
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(cls.GOOGLE_SEARCH_URL, json=payload, headers=headers)
            response.raise_for_status()
            return response.json()

    @classmethod
    async def search_profiles(cls, job_target: str, location: str, num_results: int = 10) -> List[Dict[str, Any]]:
        """
        Executa a busca estruturada de perfis e pessoas reais na web.
        Garante embaralhamento e sanitização dos resultados.
        """
        if not settings.SERPER_API_KEY:
            logger.error("SERPER_API_KEY não configurada nas variáveis de ambiente.")
            raise SearchServiceError("Chave de API de busca não configurada no servidor.")

        query = cls._build_advanced_query(job_target, location)
        
        headers = {
            "X-API-KEY": settings.SERPER_API_KEY,
            "Content-Type": "application/json",
        }
        
        # Pede uma margem maior para garantir diversidade após o embaralhamento
        payload = {
            "q": query,
            "num": max(num_results + 8, 16),
            "gl": "br",
            "hl": "pt-br"
        }

        try:
            logger.info(f"Disparando sourcing web | Alvo: {job_target} | Local: {location}")
            data = await cls._execute_request(payload, headers)
            organic_results = data.get("organic", [])
            
            if not organic_results:
                logger.warning("Nenhum resultado orgânico retornado pela API para os parâmetros informados.")
                return []

            # Embaralhamento determinístico para quebra de padrão de cache
            random.shuffle(organic_results)
            
            # Sanitização inicial dos dados brutos
            sanitized_results = []
            for item in organic_results[:num_results]:
                sanitized_results.append({
                    "title": item.get("title", "Profissional Localizado"),
                    "link": item.get("link", "#"),
                    "snippet": item.get("snippet", "Perfil extraído do radar de talentos da web aberta.")
                })

            return sanitized_results

        except httpx.HTTPStatusError as http_err:
            logger.error(f"Erro HTTP na API de Sourcing: {http_err.response.status_code} - {http_err.response.text}")
            raise SearchServiceError(f"Falha na comunicação com o provedor de busca: {http_err.response.status_code}")
        except Exception as e:
            logger.exception(f"Erro crítico não mapeado no motor de busca: {str(e)}")
            raise SearchServiceError(f"Erro interno no processamento do sourcing: {str(e)}")


# Wrapper compatível com as rotas existentes
async def search_professional_profiles(job_target: str, location: str, num_results: int = 10) -> List[Dict[str, Any]]:
    return await SearchService.search_profiles(job_target, location, num_results)