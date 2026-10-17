from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
import os
import logging

from app.services.gupy_service import process_and_notify_vagas_localiza
from app.services.whatsapp_service import send_whatsapp_dispatch
from app.core.config import settings

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

# Rota Principal: Serve o Dashboard visual do Descomplic.AI-Talentos
@app.get("/", tags=["Interface"], response_class=HTMLResponse)
async def serve_dashboard():
    if os.path.exists("index.html"):
        return FileResponse("index.html")
    return {
        "status": "online",
        "service": "Descomplic.AI Engine",
        "version": "2.1.0",
        "message": "API ativa! Certifique-se de que o index.html está na raiz do projeto.",
        "docs": "/docs"
    }

# Endpoints exigidos pelo frontend para busca de vagas e disparos
@app.post("/run-search", tags=["Campanhas"])
async def run_search(payload: dict):
    """
    Gera os kits de campanhas de acordo com os filtros selecionados na interface.
    """
    try:
        job_target = payload.get("job_target", "Atendimento ao Cliente")
        location = payload.get("location", "São Paulo - Capital")
        max_results = payload.get("max_results", 1)
        
        whatsapp_michele = getattr(settings, "MICHELE_COMPANY_WHATSAPP", "+55 31 3076-1266")
        candidates = []
        
        for i in range(max_results):
            candidates.append({
                "job_target": job_target,
                "location": location,
                "link": f"https://gupy.io/vagas/localiza-{i+1}",
                "whatsapp_link": f"https://wa.me/{whatsapp_michele.replace('+', '')}?text=Olá,%20tenho%20interesse%20na%20vaga%20de%20{job_target}"
            })
            
        return {"status": "success", "candidates": candidates}
    except Exception as e:
        logger.error(f"Erro em /run-search: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/run-dispatch", tags=["Disparos"])
async def run_dispatch(payload: dict):
    """
    Dispara os kits de atração e envia a notificação oficial via WhatsApp (Evolution API).
    """
    try:
        campaign_text = payload.get("campaign_text")
        channels = payload.get("channels", [])
        
        # Usa o número padrão da Michele caso nenhum outro seja passado
        target_phone = payload.get("candidate_phone") or getattr(settings, "MICHELE_COMPANY_WHATSAPP", "+55 31 3076-1266")
        
        logger.info(f"Pulverizando canais {channels} | Disparando WhatsApp para {target_phone}")
        
        # Envia de facto via WhatsApp integrando com a Evolution API
        await send_whatsapp_dispatch(phone_number=target_phone, message_text=campaign_text)
        
        return {
            "status": "success",
            "message": f"Campanha pulverizada nos canais ({', '.join(channels)}) e disparada com sucesso no WhatsApp!"
        }
    except Exception as e:
        logger.error(f"Erro em /run-dispatch: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Endpoints de Diagnóstico e Health Check
@app.get("/health", tags=["Health"])
def health_check():
    return {
        "status": "online",
        "service": "Descomplic.AI Engine",
        "version": "2.1.0",
        "client": "Localiza Enterprise",
    }