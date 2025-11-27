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
async def root(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        "home.html",
        {"request": request},
    )


@router.get("/home", response_class=HTMLResponse)
async def home(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        "home.html",
        {"request": request},
    )


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


@router.get("/media-gallery", response_class=HTMLResponse)
async def media_gallery_page(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        "media_gallery.html",
        {"request": request, "page_id": "media-gallery"},
    )


# Admin Routes
@router.get("/admin/login", response_class=HTMLResponse)
async def admin_login_page(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        "admin_login.html",
        {"request": request},
    )


@router.get("/admin/dashboard", response_class=HTMLResponse)
async def admin_dashboard_page(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        "admin_dashboard.html",
        {"request": request},
    )


@router.get("/admin/users", response_class=HTMLResponse)
async def admin_users_page(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        "admin_users.html",
        {"request": request},
    )


@router.get("/admin/plans", response_class=HTMLResponse)
async def admin_plans_page(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        "admin_plans.html",
        {"request": request},
    )


@router.get("/admin/coupons", response_class=HTMLResponse)
async def admin_coupons_page(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        "admin_coupons.html",
        {"request": request},
    )


@router.get("/admin/transactions", response_class=HTMLResponse)
async def admin_transactions_page(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        "admin_transactions.html",
        {"request": request},
    )


@router.get("/admin/gateways", response_class=HTMLResponse)
async def admin_gateways_page(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        "admin_gateways.html",
        {"request": request},
    )


@router.get("/admin/admins", response_class=HTMLResponse)
async def admin_admins_page(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        "admin_admins.html",
        {"request": request},
    )


@router.get("/admin/proxies", response_class=HTMLResponse)
async def admin_proxies_page(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        "admin_proxies.html",
        {"request": request},
    )


@router.get("/admin/logs", response_class=HTMLResponse)
async def admin_logs_page(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        "admin_logs.html",
        {"request": request},
    )


