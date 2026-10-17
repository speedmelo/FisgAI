import httpx
from app.core.config import settings

class WhatsAppServiceError(Exception):
    pass

async def send_whatsapp_dispatch(phone_number: str, message_text: str) -> bool:
    """
    Motor de disparo autônomo via Evolution API (Docker Local / Produção).
    Lembrete: Gupy integrada no fluxo para notificações automáticas de vagas!
    """
    api_url = getattr(settings, "WHATSAPP_API_URL", "http://localhost:8080")
    token = getattr(settings, "WHATSAPP_TOKEN", "minha_chave_secreta_123")
    instance_name = getattr(settings, "WHATSAPP_INSTANCE", "instance_descomplicai")

    # Se não houver URL configurada, fazemos fallback para simulação no console
    if not api_url:
        print(f"[SIMULAÇÃO DISPARO WHATSAPP] Para: {phone_number} | Msg: {message_text}")
        return True

    # Formato de payload exigido pela Evolution API v2
    payload = {
        "number": phone_number,
        "textMessage": {
            "text": message_text
        }
    }
    
    # Cabeçalho de autenticação oficial da Evolution API (apikey)
    headers = {
        "apikey": token,
        "Content-Type": "application/json"
    }

    url = f"{api_url}/message/sendText/{instance_name}"

    async with httpx.AsyncClient(timeout=15.0) as client:
        try:
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            return True
        except httpx.HTTPError as e:
            # Tenta capturar a resposta detalhada da API se disponível
            error_detail = e.response.text if hasattr(e, 'response') and e.response else str(e)
            raise WhatsAppServiceError(f"Erro ao disparar mensagem via Evolution API: {error_detail}")