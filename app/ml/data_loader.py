"""
ReturnShield AI — ML Data Loader

Fetches training data from the local database (PostgreSQL) 
and optionally from the Shopify API (for warm starts).
"""

import logging
import pandas as pd
from sqlalchemy import select
from app.database import async_session_factory
from app.models.return_request import ReturnRequest
from app.models.return_item import ReturnItem
from app.models.prediction import Prediction
from app.services.shopify_client import ShopifyClient

logger = logging.getLogger(__name__)

class DataLoader:
    """
    Loads training data from PostgreSQL and formats it for Pandas.
    """
    
    async def load_training_data(self, merchant_id: str) -> pd.DataFrame:
        """
        Loads return request data and associated predictions for training.
        
        Args:
            merchant_id: The UUID of the merchant.
            
        Returns:
            Pandas DataFrame with features and labels.
        """
        async with async_session_factory() as session:
            # Query return requests joined with predictions
            query = (
                select(ReturnRequest, Prediction)
                .join(Prediction, ReturnRequest.shopify_order_id == Prediction.shopify_order_id)
                .where(ReturnRequest.merchant_id == merchant_id)
            )
            
            result = await session.execute(query)
            rows = result.all()
            
            if not rows:
                logger.warning(f"No training data found for merchant {merchant_id}")
                return pd.DataFrame()
                
            data = []
            for rr, pred in rows:
                # Combine request data and prediction risk factors for training
                row = {
                    "order_id": rr.shopify_order_id,
                    "reason_code": rr.reason_code,
                    "refund_amount": float(rr.refund_amount or 0),
                    "was_returned": pred.was_returned,
                    **pred.risk_factors  # Expand risk factors as individual columns
                }
                data.append(row)
                
            return pd.DataFrame(data)

    async def fetch_historical_shopify_data(self, merchant_id: str, shop: str, access_token: str):
        """
        Fetches historical orders from Shopify and saves them as 
        synthetic training data (mock outcomes for now).
        """
        client = ShopifyClient(shop, access_token)
        orders = await client.get_historical_orders(first=50)
        
        async with async_session_factory() as session:
            for order in orders:
                # Extract numeric ID from GID
                order_id = int(order["id"].split("/")[-1])
                
                # Mock outcome: if order was refunded, was_returned = True
                total_refunded = float(order.get("totalRefundedSet", {}).get("shopMoney", {}).get("amount", 0))
                was_returned = total_refunded > 0
                
                # Create mock prediction record for feedback loop
                pred = Prediction(
                    merchant_id=merchant_id,
                    shopify_order_id=order_id,
                    risk_score=0.5, # Baseline
                    risk_factors={"historical": 1},
                    was_returned=was_returned,
                    model_version="warm-start-v1"
                )
                session.add(pred)
                
            await session.commit()
            logger.info(f"Loaded {len(orders)} historical orders for merchant {merchant_id}")
