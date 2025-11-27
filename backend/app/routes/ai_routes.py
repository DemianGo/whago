"""
Rotas para funcionalidades de IA (Inteligência Artificial).
"""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.dependencies.auth import get_current_user
from app.models.user import User
from app.services.ai_service import ai_service

router = APIRouter(prefix="/api/v1/ai", tags=["AI"])

class RewriteRequest(BaseModel):
    text: str
    tone: str = "formal"  # formal, friendly, persuasive, urgent

class RewriteResponse(BaseModel):
    original: str
    rewritten: str

class SpintaxRequest(BaseModel):
    text: str

class SpintaxResponse(BaseModel):
    original: str
    spintax: str

@router.post("/rewrite", response_model=RewriteResponse)
async def rewrite_message(
    payload: RewriteRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Reescreve uma mensagem usando IA para melhorar o tom e a persuasão.
    """
    if not payload.text:
        raise HTTPException(status_code=400, detail="Texto não pode ser vazio.")
    
    rewritten = await ai_service.rewrite_text(payload.text, payload.tone)
    
    return RewriteResponse(
        original=payload.text,
        rewritten=rewritten
    )

@router.post("/spintax", response_model=SpintaxResponse)
async def generate_spintax(
    payload: SpintaxRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Converte uma mensagem comum para formato Spintax com variações geradas por IA.
    """
    if not payload.text:
        raise HTTPException(status_code=400, detail="Texto não pode ser vazio.")
    
    spintax = await ai_service.generate_spintax(payload.text)
    
    return SpintaxResponse(
        original=payload.text,
        spintax=spintax
    )

