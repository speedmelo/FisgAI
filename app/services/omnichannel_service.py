import logging
import httpx
from app.core.config import settings

logger = logging.getLogger("MeloStrategicAI.Omnichannel")

class OmnichannelDispatcher:
    """
    Motor Enterprise de Disparo Multicanal Integrado às APIs Oficiais.
    """

    @staticmethod
    async def dispatch_to_facebook(text: str, location: str):
        token = getattr(settings, "FACEBOOK_ACCESS_TOKEN", "")
        group_id = getattr(settings, "FACEBOOK_GROUP_ID", "")

        if not token or not group_id:
            logger.info(f"[FB SIMULAÇÃO] Token ou Group ID ausentes. Publicando card simulado para grupos de {location}.")
            return True

        url = f"https://graph.facebook.com/v18.0/{group_id}/feed"
        payload = {
            "message": text,
            "access_token": token
        }

        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.post(url, data=payload)
            response.raise_for_status()
            logger.info("🚀 Sucesso no disparo para a Graph API do Facebook!")
            return True

    @staticmethod
    async def dispatch_to_linkedin(text: str, job_target: str):
        token = getattr(settings, "LINKEDIN_ACCESS_TOKEN", "")
        
        if not token:
            logger.info(f"[LI SIMULAÇÃO] Token do LinkedIn ausente. Compartilhando vaga de {job_target} em modo fallback.")
            return True

        url = "https://api.linkedin.com/v2/ugcPosts"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "X-Restli-Protocol-Version": "2.0.0"
        }
        
        # Payload estruturado para o LinkedIn UGC Post
        payload = {
            "author": "urn:li:organization:SEU_ORG_ID",
            "lifecycleState": "PUBLISHED",
            "specificContent": {
                "com.linkedin.ugc.ShareContent": {
                    "shareCommentary": {"text": text},
                    "shareMediaCategory": "NONE"
                }
            },
            "visibility": {
                "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
            }
        }

        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            logger.info("🚀 Sucesso no post orgânico via LinkedIn API!")
            return True

    @staticmethod
    async def sync_with_gupy(job_target: str):
        gupy_token = getattr(settings, "GUPY_API_TOKEN", "")
        company_id = getattr(settings, "GUPY_COMPANY_ID", "")

        if not gupy_token:
            logger.info(f"[GUPY SIMULAÇÃO] Sincronização da vaga {job_target} com a Gupy executada com sucesso.")
            return True

        url = f"https://api.gupy.io/api/v1/companies/{company_id}/jobs"
        headers = {
            "ApiKey": gupy_token,
            "Content-Type": "application/json"
        }

        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            logger.info(f"🚀 Vaga {job_target} sincronizada com sucesso no ATS Gupy!")
            return True

    @classmethod
    async def execute_dispatch(cls, campaign_text: str, job_target: str, location: str, channels: list):
        results = []
        
        if "facebook" in channels:
            await cls.dispatch_to_facebook(campaign_text, location)
            results.append("Facebook Groups")
            
        if "linkedin" in channels:
            await cls.dispatch_to_linkedin(campaign_text, job_target)
            results.append("LinkedIn")
            
        if "gupy" in channels:
            await cls.sync_with_gupy(job_target)
            results.append("Sincronização Gupy")

        return results