main py
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
import os

from app.routes.search import router as search_router
from app.services.telegram_service import send_telegram_notification


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(
    title="FisgAI Engine",
    version="2.0.0",
    description="Motor de busca e qualificação de candidatos para Localiza Enterprise",
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

# Registro central do roteador
app.include_router(search_router)


# Rota Principal: Serve o Dashboard visual do Descomplic.AI-Talentos
@app.get("/", tags=["Interface"], response_class=HTMLResponse)
async def serve_dashboard():
    if os.path.exists("index.html"):
        return FileResponse("index.html")
    return {
        "status": "online",
        "service": "FisgAI Engine",
        "version": "2.0.0",
        "message": "API ativa! Para visualizar o painel, certifique-se de que o arquivo index.html está na raiz do projeto.",
        "docs": "/docs"
    }


# Endpoints de Diagnóstico e Health Check
@app.get("/health", tags=["Health"])
def health_check():
    return {
        "status": "online",
        "service": "FisgAI Engine",
        "version": "2.0.0",
        "client": "Localiza Enterprise",
    }


@app.get("/test-telegram", tags=["Health"])
async def test_telegram():
    """Endpoint de diagnóstico para validação do pipeline do Telegram."""
    message = "🚀 <b>FisgAI Engine:</b> Conexão estabelecida com sucesso! Seu bot está ativo."
    success = await send_telegram_notification(message)
    if not success:
        raise HTTPException(
            status_code=500,
            detail="Falha ao enviar mensagem. Verifique TELEGRAM_BOT_TOKEN e TELEGRAM_CHAT_ID no .env",
        )
    return {"status": "sucesso", "message": "Notificação enviada com sucesso ao Telegram!"}
