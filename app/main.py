import logging
import os
from contextlib import asynccontextmanager

import sentry_sdk
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.api.router import router as api_router
from app.config import settings
from app.database import engine, Base

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Sentry (Optional)
if os.getenv("SENTRY_DSN"):
    try:
        import sentry_sdk
        sentry_sdk.init(
            dsn=os.getenv("SENTRY_DSN"),
            traces_sample_rate=1.0,
        )
    except ImportError:
        logger.warning("sentry-sdk not installed, skipping Sentry initialization.")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create tables on startup (Internal dev use only)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield

app = FastAPI(
    title="ReturnShield AI",
    description="AI-powered return prevention and exchanges for Shopify",
    version="1.0.0",
    lifespan=lifespan
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files and templates
app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")

# Include API routes
app.include_router(api_router)

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Serve the main dashboard."""
    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "shopify_api_key": settings.SHOPIFY_API_KEY,
        },
    )

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard_page(request: Request):
    """Serve the main dashboard (alias)."""
    return await index(request)

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
    """Analytics and insights page."""
    return templates.TemplateResponse(
        "analytics.html",
        {
            "request": request,
            "shopify_api_key": settings.SHOPIFY_API_KEY,
        },
    )

@app.get("/fit-engine", response_class=HTMLResponse)
async def fit_engine_page(request: Request):
    """Fit Engine optimization page."""
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


@app.get("/diagnostics", response_class=HTMLResponse)
async def diagnostics_page(request: Request):
    """Diagnostics page for pre-flight testing."""
    return templates.TemplateResponse(
        "diagnostics.html",
        {
            "request": request,
            "shopify_api_key": settings.SHOPIFY_API_KEY,
        },
    )
