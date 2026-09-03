from fastapi import FastAPI, BackgroundTasks
from pydantic import BaseModel
from typing import List, Optional
import urllib.parse

app = FastAPI(
    title="FisgAI Engine API",
    description="API de Recrutamento Ativo com IA e Integração WhatsApp 1-Click",
    version="1.0.0"
)

# Base de Dados em memória com o teste da Michele Silva já cadastrado
candidatos_db = [
    {
        "nome": "Michele Silva",
        "telefone": "553130761266",
        "vaga": "Atendimento / Operações",
        "score": 9.5,
        "resumo": "Perfil com excelente experiência em atendimento ao cliente e suporte operacional na região de BH.",
        "whatsapp_link": "https://wa.me/553130761266?text=Ol%C3%A1%2C%20Michele%20Silva%21%20Tudo%20bem%3F%20Vi%20seu%20perfil%20e%20notei%20sua%20excelente%20experi%C3%AAncia.%20A%20Localiza%20est%C3%A1%20com%20oportunidades%20abertas%20para%20Atendimento%20%2F%20Opera%C3%A7%C3%B5es.%20Gostaria%20de%20conversar%3F"
    }
]

class CandidatoManual(BaseModel):
    nome: str
    telefone: str
    vaga: str
    score: Optional[float] = 9.0
    resumo: Optional[str] = "Candidato inserido para validação direta do fluxo de abordagem."

def gerar_link_whatsapp(telefone: str, nome: str, vaga: str) -> str:
    # Sanitização do número
    num_limpo = "".join(filter(str.isdigit, telefone))
    if not num_limpo.startswith("55") and len(num_limpo) in [10, 11]:
        num_limpo = "55" + num_limpo
        
    mensagem = (
        f"Olá, {nome}! Tudo bem? Vi seu perfil e notei sua excelente experiência na área. "
        f"A Localiza está com oportunidades abertas para o time de {vaga} e seu perfil se destaca muito para a vaga. "
        f"Gostaria de bater um papo rápido para te contar mais detalhes?"
    )
    
    msg_encoded = urllib.parse.quote(mensagem)
    return f"https://wa.me/{num_limpo}?text={msg_encoded}"

@app.get("/")
def read_root():
    return {
        "status": "online",
        "system": "FisgAI Engine v1.0",
        "canal_ativo": "WhatsApp (wa.me 1-Click)"
    }

@app.get("/candidatos")
def listar_candidatos():
    return {
        "total": len(candidatos_db),
        "candidatos": candidatos_db
    }

@app.post("/candidatos/manual")
def adicionar_candidato_manual(candidato: CandidatoManual):
    link = gerar_link_whatsapp(candidato.telefone, candidato.nome, candidato.vaga)
    
    item = {
        "nome": candidato.nome,
        "telefone": candidato.telefone,
        "vaga": candidato.vaga,
        "score": candidato.score,
        "resumo": candidato.resumo,
        "whatsapp_link": link
    }
    
    candidatos_db.append(item)
    return {
        "status": "sucesso",
        "mensagem": "Candidato adicionado com sucesso!",
        "candidato": item
    }

@app.post("/run-search")
def run_search(background_tasks: BackgroundTasks):
    return {
        "message": "Varredura do FisgAI executada com sucesso!"
    }