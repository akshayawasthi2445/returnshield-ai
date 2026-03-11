"""
ReturnShield AI — Feature Engineering Pipeline

Prepares raw data for ML model training and inference.
"""

import pandas as pd
from sklearn.preprocessing import LabelEncoder

class FeaturePipeline:
    """
    Transforms raw data into feature vectors for XGBoost.
    """
    
    CATEGORICAL_FEATURES = ["reason_code"]
    NUMERICAL_FEATURES = ["refund_amount"]
    
    def __init__(self):
        self.label_encoders = {}
        
    def fit_transform(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Fits encoders on training data and returns transformed features.
        """
        processed_df = df.copy()
        
        # 1. Encode categorical features
        for feature in self.CATEGORICAL_FEATURES:
            if feature in processed_df.columns:
                le = LabelEncoder()
                processed_df[feature] = le.fit_transform(processed_df[feature].astype(str))
                self.label_encoders[feature] = le
        
        # 2. Extract risk factor keys if available
        # (Assuming risk_factors columns are already expanded by DataLoader)
        
        return processed_df

    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Applies learned transformations to new data (inference time).
        """
        processed_df = df.copy()
        
        for feature, le in self.label_encoders.items():
            if feature in processed_df.columns:
                # Handle unseen labels by mapping them to a default if necessary
                # For now, we assume basic categories are stable
                processed_df[feature] = le.transform(processed_df[feature].astype(str))
                
        return processed_df

    def get_feature_names(self, df: pd.DataFrame) -> list[str]:
        """Returns the list of features that should be used for training/inference."""
        # Exclude labels and IDs
        excluded = ["order_id", "was_returned"]
        return [col for col in df.columns if col not in excluded]
