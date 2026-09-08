import urllib.parse

class WhatsAppServiceError(Exception):
    pass

def build_whatsapp_link(phone: str, message: str) -> str:
    clean_phone = "".join(filter(str.isdigit, phone))
    encoded_msg = urllib.parse.quote(message)
    return f"https://wa.me/{clean_phone}?text={encoded_msg}"
