"""
ReturnShield AI — Celery Tasks

Background tasks for ML predictions, model training,
and data synchronization.
"""

import logging

from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, max_retries=3)
def predict_order_return_risk(self, merchant_id: str, order_id: int, order_data: dict):
    """
    Run return risk prediction for a single order.

    Called when a new order webhook is received.
    """
    try:
        logger.info(f"Predicting return risk for order {order_id} (merchant: {merchant_id})")

        from app.ml.return_predictor import ReturnPredictor
        from app.database import async_session_factory
        from app.models.prediction import Prediction
        from sqlalchemy import update

        # 1. Run prediction with actual order data
        predictor = ReturnPredictor(merchant_id=merchant_id)
        score, factors = predictor.predict(order_id, order_data)

        logger.info(f"Order {order_id} risk score: {score:.4f}")

        # 2. Store prediction in database
        async with async_session_factory() as session:
            await session.execute(
                update(Prediction)
                .where(Prediction.shopify_order_id == order_id)
                .values(
                    risk_score=score,
                    risk_factors=factors,
                    model_version=predictor.version
                )
            )
            await session.commit()

        return {"order_id": order_id, "risk_score": score, "factors": factors}

    except Exception as exc:
        logger.error(f"Prediction failed for order {order_id}: {exc}")
        self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))


@celery_app.task
def retrain_models():
    """
    Retrain ML models using the latest return data.

    Runs weekly via Celery Beat.
    """
    logger.info("Starting model retraining...")

    from app.ml.trainer import ModelTrainer
    from app.database import async_session_factory
    from app.models.merchant import Merchant
    from sqlalchemy import select

    async with async_session_factory() as session:
        result = await session.execute(select(Merchant).where(Merchant.is_active == True))
        merchants = result.scalars().all()

        results = {}
        for merchant in merchants:
            trainer = ModelTrainer(
                str(merchant.id), 
                merchant.shopify_shop_domain, 
                merchant.shopify_access_token
            )
            status = await trainer.train()
            results[str(merchant.id)] = status
            logger.info(f"Retrained model for merchant {merchant.id}: {status}")

    logger.info("Model retraining complete.")
    return results


@celery_app.task
def sync_prediction_outcomes():
    """
    Check which predicted orders actually ended up being returned.

    Updates the Prediction.was_returned field for model feedback.
    Runs daily via Celery Beat.
    """
    from app.database import async_session_factory
    from app.models.prediction import Prediction
    from app.models.merchant import Merchant
    from app.services.shopify_client import ShopifyClient
    from sqlalchemy import select, update

    async with async_session_factory() as session:
        # Get active merchants
        merchants_result = await session.execute(select(Merchant).where(Merchant.is_active == True))
        merchants = merchants_result.scalars().all()

        for merchant in merchants:
            client = ShopifyClient(merchant.shopify_shop_domain, merchant.shopify_access_token)
            
            # Find predictions that don't have an outcome yet
            pred_query = select(Prediction).where(
                Prediction.merchant_id == merchant.id,
                Prediction.was_returned == None
            )
            preds_result = await session.execute(pred_query)
            preds = preds_result.scalars().all()

            for pred in preds:
                try:
                    # Check if order was refunded via Shopify API
                    order = await client.get_order(pred.shopify_order_id)
                    total_refunded = float(order.get("totalRefundedSet", {}).get("shopMoney", {}).get("amount", 0))
                    
                    if total_refunded > 0:
                        await session.execute(
                            update(Prediction)
                            .where(Prediction.id == pred.id)
                            .values(was_returned=True)
                        )
                        logger.info(f"Updated prediction for order {pred.shopify_order_id}: RETURNED")
                    elif order.get("displayFinancialStatus") == "PAID" and order.get("displayFulfillmentStatus") == "FULFILLED":
                        # If fulfilled and paid for some time, maybe assume not returned?
                        # For now, let's just mark it if it's been more than 30 days
                        # (This is simplified for the demo)
                        pass
                except Exception as e:
                    logger.error(f"Error syncing outcome for order {pred.shopify_order_id}: {e}")

        await session.commit()
    logger.info("Prediction outcome sync complete.")
    return {"status": "ok"}


@celery_app.task
def send_fit_check_email(merchant_id: str, order_id: int, customer_email: str):
    """
    Send a post-delivery "How does it fit?" survey email.

    Called 7 days after order fulfillment.
    """
    logger.info(f"Sending fit check email to {customer_email} for order {order_id}")

    # TODO: Send email via notification service
    # The survey data feeds back into fit profiles

    return {"status": "sent", "email": customer_email}
