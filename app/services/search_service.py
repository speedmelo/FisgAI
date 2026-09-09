import os
import httpx
from typing import List, Dict, Any

SERPER_API_KEY = os.getenv("SERPER_API_KEY", "")

class SearchServiceError(Exception):
    pass

async def search_professional_profiles(job_target: str, location: str, num_results: int = 6) -> List[Dict[str, Any]]:
    if not SERPER_API_KEY:
        raise SearchServiceError("SERPER_API_KEY não configurada nas variáveis de ambiente.")

    # Força a busca estritamente nas vagas oficiais da Gupy da Localiza & Co junto com a região de SP
    url = "https://google.serper.dev/search"
    
    query = f"site:localiza.gupy.io {job_target} {location}"
    
    payload = {
        "q": query,
        "num": num_results,
        "gl": "br",
        "hl": "pt-br"
    }
    
    headers = {
        "X-API-KEY": SERPER_API_KEY,
        "Content-Type": "application/json"
    }

    async with httpx.AsyncClient(timeout=15.0) as client:
        try:
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()
            
            # Retorna a lista de resultados orgânicos da Gupy
            return data.get("organic", [])
        except httpx.HTTPError as e:
            raise SearchServiceError(f"Erro na comunicação com a Serper API (Gupy): {str(e)}")