import logging
import httpx
from app.services.whatsapp_service import send_whatsapp_dispatch
from app.core.config import settings

logger = logging.getLogger(__name__)

async def process_and_notify_vagas_localiza(
    candidate_phone: str, 
    search_term: str = "Localiza", 
    michele_company_whatsapp: str = None
):
    """
    Busca vagas da Localiza na Gupy e envia notificação via WhatsApp para o candidato,
    incluindo o contacto oficial de WhatsApp da empresa da Michele (+55 31 3076-1266).
    """
    gupy_api_url = f"https://portal.api.gupy.io/api/v1/jobs?name={search_term}&limit=5"
    
    # Puxa o número oficial configurado ou usa o padrão da Michele
    whatsapp_michele = michele_company_whatsapp or getattr(settings, "Localiza", "+55 31 3076-1266")
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(gupy_api_url)
            if response.status_code != 200:
                logger.error(f"Erro ao buscar vagas na Gupy: {response.text}")
                return False
                
            data = response.json()
            vagas = data.get("data", [])
        except Exception as e:
            logger.error(f"Exceção ao consultar API da Gupy: {str(e)}")
            return False

    if not vagas:
        msg = f"Olá! Não encontramos vagas abertas na Gupy para '{search_term}' neste momento."
        if whatsapp_michele:
            msg += f"\n\n📞 Podes também entrar em contacto direto com a equipe da Localiza em: {whatsapp_michele}"
        await send_whatsapp_dispatch(candidate_phone, msg)
        return True

    # Monta a mensagem formatada com as vagas encontradas
    mensagem = f"🚀 *Vagas Encontradas na Localiza (Gupy)* 🚀\n\n"
    for vaga in vagas:
        title = vaga.get("name")
        job_url = vaga.get("jobUrl")
        city = vaga.get("city", "Remoto/Brasil")
        mensagem += f"🔹 *{title}*\n📍 Local: {city}\n🔗 Candidatar-se: {job_url}\n\n"

    # Adiciona o contacto oficial da empresa da Michele
    if whatsapp_michele:
        mensagem += f"💡 *Dúvidas ou envio direto de CV?* Fala com a equipa pelo WhatsApp: {whatsapp_michele}"

    # Envia a notificação via WhatsApp
    return await send_whatsapp_dispatch(candidate_phone, mensagem)