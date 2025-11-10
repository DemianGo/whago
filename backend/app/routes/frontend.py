"""
Rotas responsáveis por servir as páginas do frontend.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates


TEMPLATES_DIR = Path(__file__).resolve().parents[2] / "frontend" / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

router = APIRouter(include_in_schema=False)


@router.get("/", response_class=HTMLResponse)
async def root(_: Request) -> RedirectResponse:
    return RedirectResponse(url="/dashboard", status_code=302)


@router.get("/login", response_class=HTMLResponse)
async def login(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        "auth_login.html",
        {"request": request},
    )


@router.get("/register", response_class=HTMLResponse)
async def register(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        "auth_register.html",
        {"request": request},
    )


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        "dashboard.html",
        {"request": request, "page_id": "dashboard"},
    )


@router.get("/chips", response_class=HTMLResponse)
async def chips(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        "chips.html",
        {"request": request, "page_id": "chips"},
    )


@router.get("/campaigns", response_class=HTMLResponse)
async def campaigns(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        "campaigns.html",
        {"request": request, "page_id": "campaigns"},
    )


@router.get("/billing", response_class=HTMLResponse)
async def billing(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        "billing.html",
        {"request": request, "page_id": "billing"},
    )


@router.get("/settings", response_class=HTMLResponse)
async def settings(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        "settings.html",
        {"request": request, "page_id": "settings"},
    )


@router.get("/reports", response_class=HTMLResponse)
async def reports_page(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        "reports.html",
        {"request": request, "page_id": "reports"},
    )


@router.get("/notifications", response_class=HTMLResponse)
async def notifications_page(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        "notifications.html",
        {"request": request, "page_id": "notifications"},
    )


@router.get("/messages", response_class=HTMLResponse)
async def messages_page(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        "messages.html",
        {"request": request, "page_id": "messages"},
    )


@router.get("/help", response_class=HTMLResponse)
async def help_page(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        "help.html",
        {"request": request, "page_id": "help"},
    )


