from fastapi import FastAPI, BackgroundTasks
from scraper import scrape_job_seekers
from ai_qualifier import CandidateQualifier
from whatsapp_linker import format_whatsapp_payload
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("fisgai_main")

app = FastAPI(title="FisgAI - Agent de Recrutamento Localiza")

# Lista em memória apenas para visualização local rápida dos candidatos fisgados
FISGADOS_DB = []

def run_pipeline():
    logger.info("🎣 FisgAI: Iniciando varredura de candidatos...")
    qualifier = CandidateQualifier()
    
    # Mineração no Google
    candidates_raw = scrape_job_seekers(max_results_per_query=3, max_queries=3)
    logger.info(f"🔍 Perfis minerados na web: {len(candidates_raw)}")
    
    for raw in candidates_raw:
        # Avaliação de IA (Gemini)
        qualified = qualifier.qualify(raw)
        
        # Filtro de aderência
        if qualified.get("score", 0) >= 6:
            # Formatação do Link de 1 Clique no WhatsApp
            final_payload = format_whatsapp_payload(qualified)
            FISGADOS_DB.append(final_payload)
            
            logger.info("--------------------------------------------------")
            logger.info(f"🎯 CANDIDATO FISGADO!")
            logger.info(f"📋 Vaga: {final_payload.get('vaga_recomendada')}")
            logger.info(f"⭐ Score: {final_payload.get('score')}/10")
            logger.info(f"📲 Link WhatsApp: {final_payload.get('whatsapp_link')}")
            logger.info("--------------------------------------------------")

@app.get("/")
def health_check():
    return {
        "status": "online",
        "system": "FisgAI Engine v1.0",
        "canal_ativo": "WhatsApp (wa.me 1-Click)"
    }

@app.post("/run-search")
def trigger_search(background_tasks: BackgroundTasks):
    background_tasks.add_task(run_pipeline)
    return {"message": "Varredura do FisgAI iniciada em segundo plano! Acompanhe no console ou na rota /candidatos"}

@app.get("/candidatos")
def get_candidatos():
    """Retorna todos os candidatos fisgados na sessão com os links de WhatsApp."""
    return {
        "total": len(FISGADOS_DB),
        "candidatos": FISGADOS_DB
    }