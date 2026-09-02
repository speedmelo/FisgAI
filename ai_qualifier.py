"""
ai_qualifier.py
Módulo de qualificação de candidatos usando a SDK oficial do Gemini.
"""

import os
import json
import urllib.parse
from typing import Dict, Any
from google import genai
from google.genai import types

class CandidateQualifier:
    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            # Em desenvolvimento local sem chave ainda, evita quebrar a inicialização
            self.client = None
        else:
            self.client = genai.Client(api_key=api_key)

    def qualify(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        if not self.client:
            return {
                "vaga_recomendada": "A verificar (Sem GEMINI_API_KEY)",
                "score": 5,
                "resumo_candidato": "Chave GEMINI_API_KEY não encontrada nas variáveis de ambiente.",
                "mensagem_whatsapp": "",
                "whatsapp_link": None,
                "original_link": raw_data.get("link")
            }

        title = raw_data.get("title", "")
        snippet = raw_data.get("snippet", "")
        phone = raw_data.get("extracted_phone")

        prompt = f"""
        Você é o recrutador especialista da Localiza&co no projeto FisgAI.
        Analise esta publicação encontrada na internet:
        Título: {title}
        Resumo: {snippet}

        REQUISITOS DAS VAGAS LOCALIZA:
        1. Vagas válidas: Atendimento ao Cliente, Auxiliar de Operações, Agente de Higienização.
        2. Requisito OBRIGATÓRIO: CNH Definitiva há no mínimo 1 ano.

        TAREFAS:
        - Defina a vaga ideal entre as 3 mencionadas.
        - Dê uma nota de compatibilidade (score de 0 a 10).
        - Escreva uma mensagem curta e persuasiva de abordagem via WhatsApp convidando o candidato para a vaga e citando os benefícios: PLR, Wellhub (Gympass) e Desconto na locação/compra de veículos.
        """

        try:
            response = self.client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema={
                        "type": "OBJECT",
                        "properties": {
                            "vaga_recomendada": {"type": "STRING"},
                            "score": {"type": "INTEGER"},
                            "resumo_candidato": {"type": "STRING"},
                            "mensagem_whatsapp": {"type": "STRING"},
                        },
                        "required": ["vaga_recomendada", "score", "resumo_candidato", "mensagem_whatsapp"]
                    }
                )
            )
            
            result = json.loads(response.text)
            
            wa_link = None
            if phone:
                encoded_msg = urllib.parse.quote(result["mensagem_whatsapp"])
                wa_link = f"https://api.whatsapp.com/send?phone={phone}&text={encoded_msg}"

            result["phone"] = phone
            result["whatsapp_link"] = wa_link
            result["original_link"] = raw_data.get("link")
            return result

        except Exception as e:
            return {
                "vaga_recomendada": "Não identificada",
                "score": 0,
                "resumo_candidato": f"Erro na análise: {str(e)}",
                "mensagem_whatsapp": "",
                "whatsapp_link": None,
                "original_link": raw_data.get("link")
            }