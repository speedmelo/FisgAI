"""
whatsapp_linker.py
Módulo responsável pela higienização de números telefônicos do Brasil
e geração de links diretos de 1 clique para abordagem via WhatsApp Web/App (wa.me).
"""

import re
import urllib.parse
from typing import Optional, Dict, Any

def clean_phone_number(phone_raw: Optional[str]) -> Optional[str]:
    """
    Remove caracteres não numéricos e garante o formato internacional DDI 55 + DDD + Número.
    Exemplo: (31) 99888-7766 -> 5531998887766
    """
    if not phone_raw:
        return None
    
    digits = re.sub(r"\D", "", phone_raw)
    
    # Se tiver 11 dígitos (Ex: 31998887766), adiciona o DDI 55 do Brasil
    if len(digits) == 11:
        return f"55{digits}"
    
    # Se já tiver 13 dígitos e começar com 55 (Ex: 5531998887766)
    if len(digits) == 13 and digits.startswith("55"):
        return digits
        
    return None

def generate_whatsapp_link(phone_raw: Optional[str], message: str) -> Optional[str]:
    """
    Gera uma URL wa.me com a mensagem codificada pronta para envio em 1 clique.
    """
    clean_phone = clean_phone_number(phone_raw)
    if not clean_phone:
        return None
        
    encoded_message = urllib.parse.quote(message)
    return f"https://wa.me/{clean_phone}?text={encoded_message}"

def format_whatsapp_payload(qualified_candidate: Dict[str, Any]) -> Dict[str, Any]:
    """
    Prepara a estrutura final do candidato fisgado com link direto de WhatsApp.
    """
    phone = qualified_candidate.get("phone")
    message = qualified_candidate.get("mensagem_whatsapp", "")
    
    wa_link = generate_whatsapp_link(phone, message)
    
    qualified_candidate["whatsapp_link"] = wa_link
    qualified_candidate["phone_formatted"] = clean_phone_number(phone)
    
    return qualified_candidate