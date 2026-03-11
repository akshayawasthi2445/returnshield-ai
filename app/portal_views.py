"""
ReturnShield AI — Customer Portal Views

Serves HTML templates for the customer-facing return portal.
"""

import uuid
from fastapi import APIRouter, Request, HTTPException, status
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.database import async_session_factory
from app.models.return_request import ReturnRequest
from app.models.return_item import ReturnItem

router = APIRouter(prefix="/portal", tags=["portal-views"])
templates = Jinja2Templates(directory="app/templates")


@router.get("/{shop_domain}", response_class=HTMLResponse)
async def portal_lookup_page(
    request: Request,
    shop_domain: str
):
    """
    Renders the order lookup page for the customer portal.
    """
    return templates.TemplateResponse(
        "portal/lookup.html",
        {
            "request": request,
            "shop_domain": shop_domain,
        },
    )


@router.get("/{shop_domain}/select", response_class=HTMLResponse)
async def portal_item_selection_page(
    request: Request,
    shop_domain: str
):
    """
    Renders the item selection page where customers pick which items to return.
    """
    # Mock order items for now
    mock_items = [
        {
            "id": 1,
            "product_title": "Premium Leather Jacket",
            "variant_title": "Large / Black",
            "image_url": "https://img.freepik.com/premium-photo/black-leather-jacket-isolated-white-background_1253488-842.jpg",
            "price": 249.99,
        },
        {
            "id": 2,
            "product_title": "Cotton Slim-Fit Chinos",
            "variant_title": "32 / Navy",
            "image_url": "https://img.freepik.com/premium-photo/navy-blue-chinos-men-white-background_1060934-2977.jpg",
            "price": 89.00,
        },
        {
            "id": 3,
            "product_title": "Silk Necktie",
            "variant_title": "Standard / Red",
            "image_url": "https://img.freepik.com/premium-photo/red-necktie-isolated-white-background_1117267-27154.jpg",
            "price": 45.00,
        }
    ]

    return templates.TemplateResponse(
        "portal/items.html",
        {
            "request": request,
            "shop_domain": shop_domain,
            "order_name": "#1234",
            "items": mock_items,
        },
    )


@router.get("/{shop_domain}/success/{return_id}", response_class=HTMLResponse)
async def portal_success_page(
    request: Request,
    shop_domain: str,
    return_id: uuid.UUID
):
    """
    Renders the success page after a customer submits a return.
    """
    async with async_session_factory() as session:
        # Fetch return request with items
        result = await session.execute(
            select(ReturnRequest)
            .options(selectinload(ReturnRequest.items))
            .where(ReturnRequest.id == return_id)
        )
        return_request = result.scalar_one_or_none()

        if return_request is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Return request not found"
            )

        return templates.TemplateResponse(
            "portal/success.html",
            {
                "request": request,
                "shop_domain": shop_domain,
                "return_request": return_request,
            },
        )


