
import json
import logging

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


class QualificationServiceError(Exception):
    """Erro durante a qualificação de um perfil."""


async def qualify_candidate(
    scraped_text: str,
    job_target: str,
) -> dict:
    if not settings.AI_API_KEY:
        raise QualificationServiceError(
            "AI_API_KEY não configurada."
        )

    if not scraped_text or not scraped_text.strip():
        raise QualificationServiceError(
            "Não há informações suficientes para analisar o perfil."
        )

    prompt = f"""
Você auxilia o RH na triagem inicial de perfis públicos.
Não invente informações e não trate suposições como fatos.
Avalie a aderência profissional à vaga: {job_target}.

Informações públicas disponíveis:
{scraped_text[:12000]}

Regras:
- Não presuma que a pessoa procura emprego atualmente.
- Não presuma que possui CNH ou ensino médio completo.
- CNH definitiva há pelo menos 1 ano é requisito obrigatório,
  mas marque como "não confirmado" se não houver evidência.
- Ensino médio completo também deve ser verificado.
- Não invente nome, telefone, experiência ou qualificações.
- A nota mede somente a aderência evidenciada no texto disponível.
- A nota não comprova que a pessoa atende aos requisitos obrigatórios.
- A mensagem é apenas uma sugestão para revisão humana; não a envie.

Retorne somente um JSON válido com esta estrutura:
{{
  "name": null,
  "score": null,
  "reason": "Limitações e evidências encontradas",
  "evidence": [],
  "requirements": {{
    "cnh_definitiva_1_ano": "confirmado, não confirmado ou não mencionado",
    "ensino_medio_completo": "confirmado, não confirmado ou não mencionado"
  }},
  "candidate_intent_verified": false,
  "approach_message": null,
  "review_required": true
}}

Use uma nota numérica entre 0 e 10 somente quando houver evidências
profissionais suficientes. Caso contrário, use null.
"""

    payload = {
        "model": settings.AI_MODEL,
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "temperature": 0,
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                settings.AI_API_URL,
                json=payload,
                headers={
                    "Authorization": f"Bearer {settings.AI_API_KEY}",
                    "Content-Type": "application/json",
                },
            )
            response.raise_for_status()
            data = response.json()
            content = data["choices"][0]["message"]["content"]

            content = content.strip()
            if content.startswith("```"):
                content = content.split("\n", 1)[-1]
                if content.endswith("```"):
                    content = content[:-3].strip()

            result = json.loads(content)

            if not isinstance(result, dict):
                raise ValueError("A resposta da IA não é um objeto JSON.")

            result["review_required"] = True
            result["candidate_intent_verified"] = False

            return result

    except (httpx.HTTPError, KeyError, IndexError, ValueError) as exc:
        logger.exception("Falha ao qualificar perfil com a IA.")
        raise QualificationServiceError(
            "Não foi possível qualificar o perfil. Tente novamente."
        ) from exc
