import httpx
from app.core.config import settings


class SearchServiceError(Exception):
    pass


async def search_professional_profiles(
    job_target: str, location: str, num_results: int = 10
):
    if not settings.SERPER_API_KEY:
        raise SearchServiceError("SERPER_API_KEY não configurada no .env")

    url = "https://google.serper.dev/search"

    # Mapeamento de variações e sinônimos operacionais da Localiza&co
    variations_map = {
        "Atendimento ao Cliente": '("Atendimento ao Cliente" OR "Agente de Atendimento" OR "Recepcionista" OR "Consultor de Atendimento")',
        "Auxiliar de Operações": '("Auxiliar de Operações" OR "Auxiliar de Pátio" OR "Agente de Pátio" OR "Manobrista" OR "Auxiliar de Logística")',
        "Agente de Higienização": '("Agente de Higienização" OR "Higienizador Automotivo" OR "Lavador de Veículos" OR "Preparador de Frota")',
        "Atendimento ao Cliente OR Auxiliar de Operações OR Agente de Higienização": '(Atendimento OR "Auxiliar de Operações" OR "Auxiliar de Pátio" OR Higienização OR Manobrista OR "Higienizador Automotivo")',
    }

    # Seleciona os termos expandidos ou utiliza a busca direta
    expanded_terms = variations_map.get(job_target, f'"{job_target}"')

    # Query Boolean Avançada: (LinkedIn OR Catho) + Variações + Região + Requisito CNH
    query = (
        f'(site:linkedin.com/in/ OR site:catho.com.br/profissionais) '
        f'{expanded_terms} '
        f'"{location}" '
        f'("CNH" OR "CNH B" OR "Carteira de Habilitação")'
    )

    headers = {
        "X-API-KEY": settings.SERPER_API_KEY,
        "Content-Type": "application/json",
    }
    payload = {"q": query, "num": num_results}

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            return data.get("organic", [])
    except Exception as e:
        raise SearchServiceError(f"Erro na busca expandida Serper: {str(e)}")