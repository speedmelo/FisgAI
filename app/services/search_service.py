import logging
import httpx
from app.core.config import settings

logger = logging.getLogger("FisgAI.SearchService")


class SearchServiceError(Exception):
    pass


async def search_professional_profiles(
    job_target: str, location: str, num_results: int = 10
):
    if not settings.SERPER_API_KEY:
        logger.error("SERPER_API_KEY não configurada no ambiente.")
        raise SearchServiceError("SERPER_API_KEY não configurada no .env")

    url = "https://google.serper.dev/search"

    # Mapeamento de variações e sinônimos operacionais da Localiza&co
    variations_map = {
        "Atendimento ao Cliente": '("Atendimento ao Cliente" OR "Agente de Atendimento" OR "Recepcionista" OR "Consultor de Atendimento")',
        "Auxiliar de Operações": '("Auxiliar de Operações" OR "Auxiliar de Pátio" OR "Agente de Pátio" OR "Manobrista" OR "Auxiliar de Logística")',
        "Agente de Higienização": '("Agente de Higienização" OR "Higienizador Automotivo" OR "Lavador de Veículos" OR "Preparador de Frota")',
        "Todas as Vagas SPA (Atendimento, Auxiliar, Higienização)": '(Atendimento OR "Auxiliar de Operações" OR "Auxiliar de Pátio" OR Higienização OR Manobrista OR "Higienizador Automotivo")',
    }

    expanded_terms = variations_map.get(job_target, f'"{job_target}"')

    headers = {
        "X-API-KEY": settings.SERPER_API_KEY,
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=15.0) as client:
        try:
            # TENTATIVA 1: Foco estrito no LinkedIn
            query_linkedin = (
                f'site:linkedin.com/in/ '
                f'{expanded_terms} '
                f'"{location}" '
                f'("CNH" OR "Habilitado" OR "Motorista")'
            )
            payload_linkedin = {
                "q": query_linkedin,
                "num": max(num_results + 4, 12),
                "gl": "br",
                "hl": "pt-br"
            }

            logger.info(f"Tentativa 1 - Sourcing LinkedIn | Cargo: {job_target}")
            resp = await client.post(url, json=payload_linkedin, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            organic = data.get("organic", [])

            if organic and len(organic) > 0:
                return organic[:num_results]

            # TENTATIVA 2 (FALLBACK INTELIGENTE): Se o LinkedIn vier vazio, busca perfis e currículos reais na web geral
            logger.warning("LinkedIn retornou vazio para esta query. Ativando fallback de busca ampla na web...")
            query_fallback = (
                f'{expanded_terms} '
                f'"{location}" '
                f'("CV" OR "Currículo" OR "Experiência" OR "CNH")'
            )
            payload_fallback = {
                "q": query_fallback,
                "num": max(num_results + 4, 12),
                "gl": "br",
                "hl": "pt-br"
            }

            resp_fb = await client.post(url, json=payload_fallback, headers=headers)
            resp_fb.raise_for_status()
            data_fb = resp_fb.json()
            organic_fb = data_fb.get("organic", [])

            return organic_fb[:num_results]

        except httpx.HTTPStatusError as http_err:
            logger.error(f"Erro HTTP na API Serper: {http_err.response.status_code} - {http_err.response.text}")
            raise SearchServiceError(f"Falha na comunicação com o provedor de busca: {http_err.response.status_code}")
        except Exception as e:
            logger.exception(f"Erro crítico no search_service: {str(e)}")
            raise SearchServiceError(f"Erro na busca de perfis via Serper: {str(e)}")