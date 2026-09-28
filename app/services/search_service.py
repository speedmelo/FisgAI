import logging
import httpx
from app.core.config import settings

logger = logging.getLogger("FisgAI.SearchService")


class SearchServiceError(Exception):
    pass


async def search_professional_profiles(
    job_target: str, location: str, num_results: int = 10
):
    safe_num = min(max(num_results, 1), 10)
    
    # Mapeamento dos cargos operacionais da Localiza para campanhas de conversão ativa
    cargos_config = {
        "Atendimento ao Cliente": {"titulo": "Atendente de Clientes & Recepção", "gupy": "https://localiza.gupy.io/jobs/atendimento-sp"},
        "Auxiliar de Operações": {"titulo": "Auxiliar de Operações & Manobrista", "gupy": "https://localiza.gupy.io/jobs/auxiliar-operacoes-sp"},
        "Agente de Higienização": {"titulo": "Agente de Higienização Automotiva", "gupy": "https://localiza.gupy.io/jobs/higienizacao-frota-sp"},
        "Todas as Vagas SPA (Atendimento, Auxiliar, Higienização)": {"titulo": "Operacional Localiza&co (Geral)", "gupy": "https://localiza.gupy.io/jobs/sp"},
    }

    config_atual = cargos_config.get(job_target, {"titulo": job_target, "gupy": "https://localiza.gupy.io/"})

    # Gerador de kits de atração ativa para a Michele
    kits_ativos = []
    bairros_sp = ["Zona Leste (Itaquera / Tatuapé)", "Zona Sul (Santo Amaro / Jabaquara)", "Zona Norte (Santana)", "Centro / República", "Guarulhos / Aeroporto", "Barueri / Alphaville"]

    for i in range(safe_num):
        bairro = bairros_sp[i % len(bairros_sp)]
        msg = f"Olá Michele, vim pelo FisgAI. Tenho interesse na vaga de {config_atual['titulo']} em {bairro} ({location}) e possuo CNH ativa. Quero agendar entrevista!"
        whatsapp_url = f"https://wa.me/553130761266?text={httpx.QueryParams({'text': msg})['text']}"
        
        kits_ativos.append({
            "title": f"Campanha Ativa: {config_atual['titulo']}",
            "link": whatsapp_url,
            "snippet": f"Região: {bairro} | Canal: Link Direto WhatsApp Michele | Requisito: CNH Válida | Status: Pronto para disparo automatizado e conversão imediata."
        })

    return kits_ativos