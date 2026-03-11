"""
ReturnShield AI — Return Predictor

ML model that predicts the probability of an order being returned.
Uses XGBoost trained on historical return data.

This is a stub implementation that returns random predictions
until the model is trained with real merchant data.
"""

import logging
import os
import random
import pandas as pd
import joblib

from app.config import settings

logger = logging.getLogger(__name__)


class ReturnPredictor:
    """
    Predicts return probability for orders.

    In production, this loads a trained XGBoost model and FeaturePipeline from disk.
    In stub mode, it returns realistic-looking random predictions.
    """

    def __init__(self, merchant_id: str | None = None):
        self.merchant_id = merchant_id
        self.model = None
        self.feature_pipeline = None
        self.version = "stub-v0.1"
        self._load_model()

    def _load_model(self) -> None:
        """Attempt to load a trained model from the model directory."""
        if not self.merchant_id:
            logger.info("No merchant_id provided. Using stub predictions.")
            return

        filename = f"return_predictor_{self.merchant_id}.joblib"
        model_path = os.path.join(settings.ML_MODEL_DIR, filename)

        if os.path.exists(model_path):
            try:
                artifacts = joblib.load(model_path)
                self.model = artifacts["model"]
                self.feature_pipeline = artifacts["feature_pipeline"]
                self.version = artifacts.get("version", "xgb-v1.0")
                logger.info(f"Loaded return predictor model for {self.merchant_id}")
            except Exception as e:
                logger.error(f"Failed to load model for {self.merchant_id}: {e}")
                self.model = None
        else:
            logger.info(f"No trained model found for {self.merchant_id}. Using stub predictions.")

    def predict(self, order_id: int, order_data: dict) -> tuple[float, dict]:
        """
        Predict return probability for an order.

        Args:
            order_id: The Shopify order ID
            order_data: Data about the order (reason, products, etc.)

        Returns:
            Tuple of (risk_score, risk_factors)
        """
        if self.model is not None and self.feature_pipeline is not None:
            try:
                # 1. Prepare features using order_data
                df = pd.DataFrame([order_data])
                processed_df = self.feature_pipeline.transform(df)
                feature_names = self.feature_pipeline.get_feature_names(processed_df)
                
                # 2. Run prediction
                X = processed_df[feature_names]
                score = float(self.model.predict_proba(X)[:, 1][0])
                
                # 3. TODO: Calculate SHAP values or similar for risk factors
                factors = {
                    "model_score": round(score, 4),
                    "confidence": "high"
                }
                return score, factors
            except Exception as e:
                logger.error(f"Prediction failed for order {order_id}: {e}")

        # Fallback to stub prediction
        score = random.betavariate(2, 5)
        score = round(score, 4)
        factors = {
            "product_category_risk": round(random.uniform(0, 0.3), 3),
            "size_mismatch_signal": round(random.uniform(0, 0.25), 3),
            "customer_return_history": round(random.uniform(0, 0.2), 2),
            "is_stub": True
        }
        return score, factors
