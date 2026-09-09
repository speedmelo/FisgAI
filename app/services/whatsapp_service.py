import httpx
from app.core.config import settings

class WhatsAppServiceError(Exception):
    pass

async def send_whatsapp_dispatch(phone_number: str, message_text: str) -> bool:
    """
    Motor de disparo autônomo via API de WhatsApp (Compatível com Z-API, Evolution ou Proxies REST).
    """
    # Você pode configurar WHATSAPP_API_URL e WHATSAPP_TOKEN no seu .env do Render
    api_url = getattr(settings, "WHATSAPP_API_URL", "")
    token = getattr(settings, "WHATSAPP_TOKEN", "")

    if not api_url or not token:
        # Modo Fallback / Log de simulação caso as credenciais da API de disparo ainda não estejam no .env
        print(f"[SIMULAÇÃO DISPARO API] Para: {phone_number} | Msg: {message_text}")
        return True

    payload = {
        "phone": phone_number,
        "message": message_text
    }
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    async with httpx.AsyncClient(timeout=15.0) as client:
        try:
            response = await client.post(api_url, json=payload, headers=headers)
            response.raise_for_status()
            return True
        except httpx.HTTPError as e:
            raise WhatsAppServiceError(f"Erro ao disparar mensagem via WhatsApp API: {str(e)}")