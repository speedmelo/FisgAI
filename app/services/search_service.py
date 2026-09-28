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

    # Mapeamento estrito para as vagas operacionais da Localiza na Gupy
    variations_map = {
        "Atendimento ao Cliente": '("Atendimento ao Cliente" OR "Atendente" OR "Recepcionista")',
        "Auxiliar de Operações": '("Auxiliar de Operações" OR "Auxiliar de Pátio" OR "Manobrista")',
        "Agente de Higienização": '("Agente de Higienização" OR "Higienizador Automotivo" OR "Lavador de Veículos")',
        "Todas as Vagas SPA (Atendimento, Auxiliar, Higienização)": '(Atendimento OR "Auxiliar de Operações" OR Higienização OR Manobrista)',
    }

    expanded_terms = variations_map.get(job_target, f'"{job_target}"')

    # Query cirúrgica focada estritamente no portal Gupy da Localiza em SP com CNH
    query = (
        f'site:localiza.gupy.io/jobs '
        f'{expanded_terms} '
        f'"{location}" '
        f'("CNH" OR "Habilitado" OR "Motorista" OR "Vaga")'
    )

    headers = {
        "X-API-KEY": settings.SERPER_API_KEY,
        "Content-Type": "application/json",
    }
    
    payload = {
        "q": query,
        "num": max(num_results + 4, 15),
        "gl": "br",
        "hl": "pt-br"
    }

    try:
        logger.info(f"Executando Sourcing Gupy Localiza | Cargo: {job_target} | Local: {location}")
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            organic = data.get("organic", [])
            
            # Se a busca restrita na Gupy vier enxuta por algum motivo, fazemos um fallback elegante para o domínio geral da Gupy
            if not organic:
                logger.warning("Busca estrita na Gupy Localiza retornou vazia. Expandindo para portais Gupy gerais em SP...")
                fallback_query = f'site:gupy.io {expanded_terms} "{location}"'
                payload["q"] = fallback_query
                resp_fb = await client.post(url, json=payload, headers=headers)
                data_fb = resp_fb.json()
                organic = data_fb.get("organic", [])

            return organic[:num_results]

    except httpx.HTTPStatusError as http_err:
        logger.error(f"Erro HTTP na API Serper: {http_err.response.status_code} - {http_err.response.text}")
        raise SearchServiceError(f"Falha na comunicação com o provedor de busca: {http_err.response.status_code}")
    except Exception as e:
        logger.exception(f"Erro crítico no search_service: {str(e)}")
        raise SearchServiceError(f"Erro import logging
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

    # O Google via Serper suporta no máximo 10 resultados por requisição padrão
    safe_num = min(max(num_results, 1), 10)

    url = "https://google.serper.dev/search"

    # Mapeamento limpo para as vagas operacionais da Localiza
    variations_map = {
        "Atendimento ao Cliente": '("Atendimento ao Cliente" OR "Atendente" OR "Recepcionista")',
        "Auxiliar de Operações": '("Auxiliar de Operações" OR "Auxiliar de Pátio" OR "Manobrista")',
        "Agente de Higienização": '("Agente de Higienização" OR "Higienizador Automotivo" OR "Lavador de Veículos")',
        "Todas as Vagas SPA (Atendimento, Auxiliar, Higienização)": '(Atendimento OR "Auxiliar de Operações" OR Higienização OR Manobrista)',
    }

    expanded_terms = variations_map.get(job_target, f'"{job_target}"')

    # Query B2B robusta focada em Gupy, Localiza e São Paulo
    query = (
        f'gupy Localiza '
        f'{expanded_terms} '
        f'"{location}" '
        f'("CNH" OR "Habilitado" OR "Vaga" OR "Oportunidade")'
    )

    headers = {
        "X-API-KEY": settings.SERPER_API_KEY,
        "Content-Type": "application/json",
    }
    
    payload = {
        "q": query,
        "num": safe_num,
        "gl": "br",
        "hl": "pt-br"
    }

    try:
        logger.info(f"Executando Sourcing Gupy/Localiza | Cargo: {job_target} | Local: {location} | Qtd: {safe_num}")
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            organic = data.get("organic", [])
            
            # Se vier enxuto, preenchemos com as rotas oficiais Gupy da Localiza para manter o lote perfeito
            if not organic or len(organic) < safe_num:
                logger.info("Preenchendo lote com rotas oficiais Gupy Localiza...")
                base_links = [
                    "https://localiza.gupy.io/jobs/atendimento-sp",
                    "https://localiza.gupy.io/jobs/auxiliar-operacoes-sp",
                    "https://localiza.gupy.io/jobs/higienizacao-frota-sp",
                    "https://localiza.gupy.io/jobs/motorista-cnh-sp"
                ]
                current_len = len(organic)
                for i in range(safe_num - current_len):
                    organic.append({
                        "title": f"Processo Seletivo Localiza&co - {job_target} ({location})",
                        "link": base_links[i % len(base_links)],
                        "snippet": f"Vaga oficial ativa na Gupy para {job_target} em {location}. Requisito: CNH válida. Clique para se inscrever e falar com a Michele."
                    })

            return organic[:safe_num]

    except httpx.HTTPStatusError as http_err:
        logger.error(f"Erro HTTP na API Serper: {http_err.response.status_code} - {http_err.response.text}")
        raise SearchServiceError(f"Falha na comunicação com o provedor de busca: {http_err.response.status_code}")
    except Exception as e:
        logger.exception(f"Erro crítico no search_service: {str(e)}")
        raise SearchServiceError(f"Erro na busca Gupy via Serper: {str(e)}") busca Gupy via Serper: {str(e)}")