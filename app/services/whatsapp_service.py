
import logging

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


class WhatsAppServiceError(Exception):
    """Erro ao enviar mensagem pela Evolution API."""


async def send_whatsapp_dispatch(
    phone_number: str,
    message_text: str,
) -> bool:
    """Envia uma mensagem pela Evolution API."""

    api_url = str(
        getattr(settings, "WHATSAPP_API_URL", "") or ""
    ).strip().rstrip("/")

    token = str(
        getattr(settings, "WHATSAPP_TOKEN", "") or ""
    ).strip()

    instance_name = str(
        getattr(settings, "WHATSAPP_INSTANCE", "") or ""
    ).strip()

    if not api_url or not token or not instance_name:
        raise WhatsAppServiceError(
            "WhatsApp não configurado. Verifique "
            "WHATSAPP_API_URL, WHATSAPP_TOKEN e WHATSAPP_INSTANCE."
        )

    phone_number = str(phone_number or "").strip()
    message_text = str(message_text or "").strip()

    if not phone_number:
        raise WhatsAppServiceError("Informe o telefone de destino.")

    if not message_text:
        raise WhatsAppServiceError("A mensagem não pode estar vazia.")

    payload = {
        "number": phone_number,
        "text": message_text,
    }

    headers = {
        "apikey": token,
        "Content-Type": "application/json",
    }

    url = f"{api_url}/message/sendText/{instance_name}"

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(
                url,
                json=payload,
                headers=headers,
            )
            response.raise_for_status()

    except httpx.HTTPStatusError as exc:
        logger.error(
            "Evolution API retornou HTTP %s.",
            exc.response.status_code,
        )
        raise WhatsAppServiceError(
            f"Evolution API recusou a solicitação "
            f"(HTTP {exc.response.status_code})."
        ) from exc

    except httpx.RequestError as exc:
        logger.error("Falha de conexão com a Evolution API.")
        raise WhatsAppServiceError(
            "Não foi possível conectar à Evolution API. "
            "Verifique a URL e a disponibilidade do serviço."
        ) from exc

    return True
