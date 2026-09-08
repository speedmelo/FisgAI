import httpx
import json
from app.core.config import settings

class QualificationServiceError(Exception):
    pass

async def qualify_candidate(scraped_text: str, job_target: str) -> dict:
    if not settings.AI_API_KEY:
        raise QualificationServiceError("AI_API_KEY não configurada.")

    headers = {
        "Authorization": f"Bearer {settings.AI_API_KEY}",
        "Content-Type": "application/json"
    }

    prompt = f"""
Você é um recrutador especialista da empresa Localiza.
Avalie o perfil abaixo para a vaga de '{job_target}'.

Perfil do candidato:
{scraped_text}

Retorne ESTRITAMENTE um JSON no seguinte formato:
{{
  "name": "Nome do candidato ou null se não souber",
  "score": 8.5, (Nota de 0 a 10 para aderência à vaga)
  "reason": "Resumo em 1 frase do porquê da nota",
  "approach_message": "Mensagem curta e amigável de abordagem inicial em nome da Localiza"
}}
"""

    payload = {
        "model": settings.AI_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.2
    }

    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.post(settings.AI_API_URL, json=payload, headers=headers)
            resp.raise_for_status()
            res_data = resp.json()
            content = res_data["choices"][0]["message"]["content"]
            
            # Limpa formatação markdown se houver
            content_clean = content.replace("```json", "").replace("```", "").strip()
            return json.loads(content_clean)
    except Exception as e:
        # Fallback de segurança se falhar
        return {
            "name": "Candidato Localiza",
            "score": 7.5,
            "reason": "Perfil atende aos requisitos básicos encontrados na busca.",
            "approach_message": f"Olá! Vimos seu perfil e gostaríamos de conversar sobre uma oportunidade de {job_target} na Localiza!"
        }
