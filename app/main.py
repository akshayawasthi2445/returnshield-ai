"""
ReturnShield AI — FastAPI Application Entrypoint

Main application that wires together all routes, templates,
and middleware for the Shopify embedded app.
"""

import logging
from contextlib import asynccontextmanager

import sentry_sdk
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.api.router import router as api_router
from app.auth.oauth import router as auth_router
from app.portal_views import router as portal_views_router
from app.config import settings

# --- Logging ---
logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


# --- Sentry (optional) ---
if settings.SENTRY_DSN:
    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        traces_sample_rate=0.1,
        environment=settings.APP_ENV,
    )


# --- Lifespan ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown events."""
    logger.info(f"🛡️  {settings.APP_NAME} starting up...")
    logger.info(f"   Environment: {settings.APP_ENV}")
    logger.info(f"   App URL: {settings.APP_URL}")
    yield
    logger.info(f"🛡️  {settings.APP_NAME} shutting down...")


# --- App ---
app = FastAPI(
    title=settings.APP_NAME,
    description="AI-Powered Returns & Exchange Autopilot for Shopify",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
)

# Mount static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Templates
templates = Jinja2Templates(directory="app/templates")

# Include routers
app.include_router(auth_router)
app.include_router(api_router)
app.include_router(portal_views_router)


# --- Health Check ---
@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring."""
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "version": "0.1.0",
        "environment": settings.APP_ENV,
    }


# --- Page Routes (serve embedded app templates) ---

@app.get("/", response_class=HTMLResponse)
@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard_page(request: Request):
    """Main dashboard page."""
    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "shopify_api_key": settings.SHOPIFY_API_KEY,
        },
    )


@app.get("/returns", response_class=HTMLResponse)
async def returns_page(request: Request):
    """Returns management page."""
    return templates.TemplateResponse(
        "returns.html",
        {
            "request": request,
            "shopify_api_key": settings.SHOPIFY_API_KEY,
        },
    )


@app.get("/analytics", response_class=HTMLResponse)
async def analytics_page(request: Request):
    """Analytics page."""
    return templates.TemplateResponse(
        "analytics.html",
        {
            "request": request,
            "shopify_api_key": settings.SHOPIFY_API_KEY,
        },
    )


@app.get("/fit-engine", response_class=HTMLResponse)
async def fit_engine_page(request: Request):
    """Fit engine configuration page."""
    return templates.TemplateResponse(
        "fit_engine.html",
        {
            "request": request,
            "shopify_api_key": settings.SHOPIFY_API_KEY,
        },
    )


@app.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request):
    """Settings page."""
    return templates.TemplateResponse(
        "settings.html",
        {
            "request": request,
            "shopify_api_key": settings.SHOPIFY_API_KEY,
        },
    )
