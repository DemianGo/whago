"""
Payment Routes

Endpoints para gerenciar pagamentos, assinaturas e webhooks.
"""

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any

from ..database import get_db
from ..dependencies.auth import get_current_user
from ..models.user import User
from ..services.payment_service import PaymentService
from ..services.payment_gateways import PaymentMethod
from ..schemas.payment import (
    CreateSubscriptionRequest,
    CreateSubscriptionResponse,
    CancelSubscriptionResponse,
    PurchaseCreditsRequest,
    PurchaseCreditsResponse,
    PaymentMethodsResponse,
)


router = APIRouter(prefix="/api/v1/payments", tags=["payments"])


@router.get("/methods", response_model=PaymentMethodsResponse)
async def get_payment_methods():
    """
    Lista métodos de pagamento disponíveis.
    """
    return {
        "methods": [
            {
                "id": "mercadopago",
                "name": "Mercado Pago",
                "logo": "/static/images/mercadopago-logo.png",
                "enabled": True,
            },
            {
                "id": "paypal",
                "name": "PayPal",
                "logo": "/static/images/paypal-logo.png",
                "enabled": False,  # A implementar
            },
            {
                "id": "stripe",
                "name": "Stripe",
                "logo": "/static/images/stripe-logo.png",
                "enabled": False,  # A implementar
            },
        ]
    }


@router.post("/subscriptions", response_model=CreateSubscriptionResponse, status_code=status.HTTP_201_CREATED)
async def create_subscription(
    request: CreateSubscriptionRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Cria assinatura recorrente para um plano.
    
    O usuário será redirecionado para a URL de pagamento retornada.
    """
    payment_service = PaymentService(db)
    
    try:
        payment_method = PaymentMethod(request.payment_method)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Método de pagamento '{request.payment_method}' não suportado"
        )
    
    try:
        result = await payment_service.create_subscription(
            user=current_user,
            plan_id=request.plan_id,
            payment_method=payment_method
        )
        
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao criar assinatura: {str(e)}"
        )


@router.delete("/subscriptions", response_model=CancelSubscriptionResponse)
async def cancel_subscription(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Cancela assinatura recorrente do usuário.
    
    A assinatura será cancelada imediatamente, mas o acesso ao plano
    permanece até o fim do período já pago.
    """
    payment_service = PaymentService(db)
    
    try:
        result = await payment_service.cancel_subscription(user=current_user)
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao cancelar assinatura: {str(e)}"
        )


@router.post("/credits", response_model=PurchaseCreditsResponse, status_code=status.HTTP_201_CREATED)
async def purchase_credits(
    request: PurchaseCreditsRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Compra créditos avulsos.
    
    O usuário será redirecionado para a URL de pagamento retornada.
    Após aprovação, os créditos serão adicionados automaticamente.
    """
    payment_service = PaymentService(db)
    
    if request.credits <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Quantidade de créditos deve ser maior que zero"
        )
    
    try:
        payment_method = PaymentMethod(request.payment_method)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Método de pagamento '{request.payment_method}' não suportado"
        )
    
    try:
        result = await payment_service.purchase_credits(
            user=current_user,
            credits=request.credits,
            payment_method=payment_method
        )
        
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao processar compra: {str(e)}"
        )


@router.post("/webhook/{gateway}", status_code=status.HTTP_200_OK)
async def payment_webhook(
    gateway: str,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Webhook para receber notificações de pagamento dos gateways.
    
    Suporta: mercadopago, paypal, stripe
    """
    try:
        payment_method = PaymentMethod(gateway)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Gateway '{gateway}' não suportado"
        )
    
    # Obter payload e headers
    payload = await request.json()
    headers = dict(request.headers)
    
    payment_service = PaymentService(db)
    
    try:
        result = await payment_service.process_webhook(
            payment_method=payment_method,
            payload=payload,
            headers=headers
        )
        
        return {"status": "ok", "event": result.get("event_type")}
    except ValueError as e:
        # Assinatura inválida
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )
    except Exception as e:
        # Log do erro mas retorna 200 para não reenviar webhook
        print(f"Erro ao processar webhook: {e}")
        return {"status": "error", "message": str(e)}

