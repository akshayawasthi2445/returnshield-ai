from fastapi import APIRouter

from app.api.v1 import analytics, diagnostics, exchanges, fit_engine, portal, predictions, returns, webhooks

router = APIRouter(prefix="/api/v1")

router.include_router(webhooks.router)
router.include_router(returns.router)
router.include_router(exchanges.router)
router.include_router(predictions.router)
router.include_router(analytics.router)
router.include_router(fit_engine.router)
router.include_router(portal.router)
router.include_router(diagnostics.router)
