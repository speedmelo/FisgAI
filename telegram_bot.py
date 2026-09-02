import os
import httpx

def send_telegram_alert(candidate_data: dict) -> bool:
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    
    if not token or not chat_id:
        print("Telegram Token ou Chat ID ausente.")
        return False

    vaga = candidate_data.get("vaga_recomendada", "Geral")
    score = candidate_data.get("score", 0)
    resumo = candidate_data.get("resumo_candidato", "")
    wa_link = candidate_data.get("whatsapp_link")
    orig_link = candidate_data.get("original_link")

    message = f"🎯 *CANDIDATO FISGADO - FISGAI*\n\n"
    message += f"📋 *Vaga Sugerida:* {vaga}\n"
    message += f"⭐ *Compatibilidade:* {score}/10\n"
    message += f"📝 *Resumo:* {resumo}\n\n"
    
    if wa_link:
        message += f"📲 [ABRIR NO WHATSAPP E ABORDAR]({wa_link})\n"
    else:
        message += f"🔗 [VER POST / PERFIL PÚBLICO]({orig_link})\n"

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "Markdown",
        "disable_web_page_preview": True
    }

    try:
        r = httpx.post(url, json=payload, timeout=10.0)
        return r.status_code == 200
    except Exception as e:
        print(f"Erro ao enviar Telegram: {e}")
        return False