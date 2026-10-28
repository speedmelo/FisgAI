
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
import os
import logging

from app.routes.search import router as search_router
from app.services.whatsapp_service import send_whatsapp_dispatch
from app.core.config import settings
from campaigns import LOCALIZA_CAMPAIGN

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(
    title="Descomplic.AI Engine",
    version="2.1.0",
    description="Motor de atração de talentos e automação omnichannel para Localiza & Co",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", tags=["Interface"], response_class=HTMLResponse)
async def serve_dashboard():
    if os.path.exists("index.html"):
        return FileResponse("index.html")

    return {
        "status": "online",
        "service": "Descomplic.AI Engine",
        "version": "2.1.0",
        "message": "API ativa! Verifique se index.html está na raiz do projeto.",
        "docs": "/docs",
    }


# Registra somente as rotas de busca corrigidas.
# Não registra o router inteiro, pois ele também pode conter
# uma rota de disparo independente.
for route in search_router.routes:
    if getattr(route, "path", None) == "/run-search":
        app.router.routes.append(route)


@app.post("/run-dispatch", tags=["Disparos"])
async def run_dispatch(payload: dict):
    """
    Disparo explícito de campanha.
    Esta rota não é chamada pela busca.
    """
    try:
        campaign_text = str(
            payload.get("campaign_text") or LOCALIZA_CAMPAIGN
        ).strip()

        channels = payload.get("channels", [])

        target_phone = (
            payload.get("candidate_phone")
            or getattr(settings, "MICHELE_COMPANY_WHATSAPP", None)
        )

        if not target_phone:
            raise HTTPException(
                status_code=422,
                detail="Informe candidate_phone ou configure o número de destino.",
            )

        if not campaign_text:
            raise HTTPException(
                status_code=422,
                detail="O texto da campanha não pode estar vazio.",
            )

        logger.info(
            "Disparo solicitado explicitamente. Canais: %s",
            channels,
        )

        await send_whatsapp_dispatch(
            phone_number=target_phone,
            message_text=campaign_text,
        )

        return {
            "status": "success",
            "message": "Disparo solicitado e processado pelo serviço de WhatsApp.",
        }

    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Erro em /run-dispatch")
        raise HTTPException(
            status_code=500,
            detail="Não foi possível executar o disparo.",
        ) from exc


@app.get("/health", tags=["Health"])
def health_check():
    return {
        "status": "online",
        "service": "Descomplic.AI Engine",
        "version": "2.1.0",
        "client": "Localiza Enterprise",
    }
