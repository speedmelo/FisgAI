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

    # Pool de termos para buscar currículos e pessoas reais na web aberta
    keywords_pool = [
        "currículo", "experiência", "profissional", "candidato", "trabalho em são paulo", "perfil profissional"
    ]
    random_keyword = random.choice(keywords_pool)

    # Query ultra focada: Gupy Oficial da Localiza + Buscas de pessoas reais/currículos na web (sem linkedin)
    query = (
        f'(site:localiza.gupy.io OR "currículo" OR "perfil") '
        f'("{job_target}") '
        f'("{location}") '
        f'("CNH" OR "Habilitado" OR "Motorista") '
        f'("{random_keyword}") '
        f'(-site:linkedin.com)'  # Garante exclusão total do LinkedIn
    )

    headers = {
        "X-API-KEY": settings.SERPER_API_KEY,
        "Content-Type": "application/json",
    }
    
    # Pede um volume robusto para a API para termos bastante margem
    payload = {"q": query, "num": max(num_results + 6, 12)}

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            organic_results = data.get("organic", [])
            
            # Embaralha para trazer variedade a cada execução
            random.shuffle(organic_results)
            return organic_results[:num_results]
            
    except Exception as e:
        raise SearchServiceError(f"Erro na busca Gupy/Web: {str(e)}")