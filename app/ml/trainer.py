"""
ReturnShield AI — Model Trainer

Coordinates the ML training lifecycle:
1. Load data via DataLoader
2. Transform features via FeaturePipeline
3. Train XGBoost model
4. Serialize model and pipeline to disk
"""

import os
import joblib
import logging
import xgboost as xgb
from sklearn.model_selection import train_test_split
from sklearn.metrics import roc_auc_score

from app.config import settings
from app.ml.data_loader import DataLoader
from app.ml.features import FeaturePipeline

logger = logging.getLogger(__name__)

class ModelTrainer:
    """
    Coordinates model training for a specific merchant.
    """
    
    def __init__(self, merchant_id: str, shop_domain: str | None = None, access_token: str | None = None):
        self.merchant_id = merchant_id
        self.shop_domain = shop_domain
        self.access_token = access_token
        self.data_loader = DataLoader()
        self.feature_pipeline = FeaturePipeline()
        self.model = None
        
    async def train(self) -> dict:
        """
        Runs the full training pipeline.
        
        Returns:
            dict with training metrics (AUC, accuracy, etc.)
        """
        logger.info(f"Starting model training for merchant {self.merchant_id}")
        
        # 1. Load Data
        df = await self.data_loader.load_training_data(self.merchant_id)
        
        # Trigger Warm Start if no data found and credentials provided
        if df.empty and self.shop_domain and self.access_token:
            logger.info(f"DB empty for {self.merchant_id}. Triggering warm start...")
            await self.data_loader.fetch_historical_shopify_data(
                self.merchant_id, self.shop_domain, self.access_token
            )
            df = await self.data_loader.load_training_data(self.merchant_id)

        if df.empty or len(df) < 5:  # Minimum threshold for training
            logger.warning(f"Insufficient data for training (found {len(df)} records)")
            return {"status": "insufficient_data", "count": len(df)}
            
        # 2. Fit Transform Features
        processed_df = self.feature_pipeline.fit_transform(df)
        feature_names = self.feature_pipeline.get_feature_names(processed_df)
        
        X = processed_df[feature_names]
        y = processed_df["was_returned"].fillna(False).astype(int)
        
        # 3. Train/Test Split
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42
        )
        
        # 4. Train XGBoost Model
        self.model = xgb.XGBClassifier(
            n_estimators=100,
            max_depth=5,
            learning_rate=0.1,
            objective="binary:logistic",
            random_state=42
        )
        
        self.model.fit(X_train, y_train)
        
        # 5. Evaluate
        y_pred = self.model.predict_proba(X_test)[:, 1]
        auc = roc_auc_score(y_test, y_pred) if len(set(y_test)) > 1 else 0.0
        
        logger.info(f"Training complete. AUC: {auc:.4f}")
        
        # 6. Save Artifacts
        self._save_model()
        
        return {
            "status": "success",
            "auc": auc,
            "training_samples": len(X_train),
            "test_samples": len(X_test),
            "model_path": self._get_model_path()
        }

    def _get_model_path(self) -> str:
        """Returns the local path for the merchant's model file."""
        filename = f"return_predictor_{self.merchant_id}.joblib"
        return os.path.join(settings.ML_MODEL_DIR, filename)

    def _save_model(self) -> None:
        """Serializes the model and feature pipeline to disk."""
        model_path = self._get_model_path()
        
        # We save both the model and the feature pipeline together
        # so transformations are consistent at inference time
        artifacts = {
            "model": self.model,
            "feature_pipeline": self.feature_pipeline,
            "version": "xgb-v1.0"
        }
        
        joblib.dump(artifacts, model_path)
        logger.info(f"Model saved to {model_path}")
