import httpx
import random
from app.core.config import settings


class SearchServiceError(Exception):
    pass


async def search_professional_profiles(
    job_target: str, location: str, num_results: int = 10
):
    if not settings.SERPER_API_KEY:
        raise SearchServiceError("SERPER_API_KEY não configurada no .env")

    url = "https://google.serper.dev/search"

    keywords_pool = ["currículo", "experiência", "profissional", "trabalho", "perfil", "candidato"]
    random_keyword = random.choice(keywords_pool)

    query = (
        f'("{job_target}") '
        f'("{location}") '
        f'("CNH" OR "Habilitado" OR "Motorista") '
        f'("{random_keyword}") '
        f'(-site:gupy.io -site:vagas.com.br)'
    )

    headers = {
        "X-API-KEY": settings.SERPER_API_KEY,
        "Content-Type": "application/json",
    }
    
    payload = {"q": query, "num": max(num_results + 4, 10)}

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            organic_results = data.get("organic", [])
            random.shuffle(organic_results)
            return organic_results[:num_results]
            
    except Exception as e:
        raise SearchServiceError(f"Erro na busca Serper: {str(e)}")