from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List
from app.services.whatsapp_service import send_whatsapp_dispatch, WhatsAppServiceError

router = APIRouter(prefix="", tags=["WhatsApp Dispatch"])

class DispatchRequest(BaseModel):
    recipients: List[str] = Field(..., description="Lista de números de telefone de destino com DDI e DDD")
    message: str = Field(..., description="Texto magnético da campanha de recrutamento")

class DispatchResponse(BaseModel):
    success: bool
    dispatched_count: int
    message: str

@router.post("/run-dispatch", response_model=DispatchResponse)
async def run_dispatch(request: DispatchRequest):
    success_count = 0
    try:
        for phone in request.recipients:
            await send_whatsapp_dispatch(phone_number=phone, message_text=request.message)
            success_count += 1
            
        return DispatchResponse(
            success=True,
            dispatched_count=success_count,
            message=f"Campanha disparada com sucesso para {success_count} contato(s)!"
        )
    except WhatsAppServiceError as e:
        raise HTTPException(status_code=500, detail=str(e))