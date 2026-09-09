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

    # Mapeamento estrito de cargos operacionais para perfis de pessoas
    job_aliases = {
        "Atendimento ao Cliente": '("Atendimento ao Cliente" OR "Recepcionista" OR "Atendente")',
        "Auxiliar de Operações": '("Auxiliar de Operações" OR "Auxiliar de Pátio" OR "Manobrista")',
        "Agente de Higienização": '("Agente de Higienização" OR "Higienizador Automotivo" OR "Lavador de Veículos")',
        "Todas as Vagas SPA (Atendimento, Auxiliar, Higienização)": '(Atendimento OR "Auxiliar de Operações" OR Higienização OR Manobrista)',
    }
    
    target_query = job_aliases.get(job_target, f'"{job_target}"')

    # Termos de rotação focados em perfis pessoais/currículos reais na web
    resume_keywords = [
        "currículo", "experiência profissional", "resumo profissional", "portfólio", "contato", "sobre mim"
    ]
    random_keyword = random.choice(resume_keywords)

    # Query cirúrgica: Focada em PESSOAS REAIS / CURRÍCULOS, bloqueando páginas de portais corporativos de vagas
    query = (
        f'{target_query} '
        f'("{location}") '
        f'("CNH" OR "Habilitado" OR "Categoria B") '
        f'("{random_keyword}") '
        f'(-site:gupy.io -site:vagas.com.br -site:indeed.com -site:catho.com.br -site:linkedin.com/company -site:glassdoor.com.br -intitle:"vaga" -intitle:"oportunidade")'
    )

    headers = {
        "X-API-KEY": settings.SERPER_API_KEY,
        "Content-Type": "application/json",
    }
    
    # Pede uma margem de segurança maior para filtrar na unha
    payload = {"q": query, "num": max(num_results + 8, 18)}

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            organic_results = data.get("organic", [])
            
            # Filtro adicional de segurança no código: descarta resultados que tenham cara de anúncio de vaga corporativa
            filtered_results = []
            for item in organic_results:
                title = item.get("title", "").lower()
                snippet = item.get("snippet", "").lower()
                
                # Se o título for uma vaga genérica de empresa, pula
                if "vaga para" in title or "oportunidade de emprego na" in title or "trabalhe conosco" in title:
                    continue
                    
                filtered_results.append(item)

            # Embaralha para dar dinamismo
            random.shuffle(filtered_results)
            
            # Se a filtragem estrita deixar a lista menor que o pedido, usa o que tem ou complementa com os orgânicos puros
            final_pool = filtered_results if len(filtered_results) >= num_results else organic_results
            random.shuffle(final_pool)
            
            return final_pool[:num_results]
            
    except Exception as e:
        raise SearchServiceError(f"Erro na busca de candidatos reais: {str(e)}")