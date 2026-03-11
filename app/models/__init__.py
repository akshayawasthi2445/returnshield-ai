"""ReturnShield AI — Models Package."""

from app.models.base import BaseModel
from app.models.exchange import Exchange
from app.models.merchant import Merchant
from app.models.prediction import Prediction
from app.models.product_fit import ProductFitProfile
from app.models.return_item import ReturnItem
from app.models.return_request import ReturnRequest

__all__ = [
    "BaseModel",
    "Exchange",
    "Merchant",
    "Prediction",
    "ProductFitProfile",
    "ReturnItem",
    "ReturnRequest",
]
