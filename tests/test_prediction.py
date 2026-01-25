import unittest
from unittest.mock import MagicMock, patch, mock_open
import os
import pandas as pd
import numpy as np
import joblib
from datetime import datetime, timezone, timedelta

class TestPrediction(unittest.TestCase):
    
    def setUp(self):
        self.export_dir = "data/exports"
        self.model_dir = "data/models"
        os.makedirs(self.export_dir, exist_ok=True)
        os.makedirs(self.model_dir, exist_ok=True)
        
    def test_prepare_features(self):
        from app.ml.prediction import prepare_features
        
        # Create mock DataFrame
        now = datetime.now(timezone.utc)
        data = []
        for i in range(20):
            data.append({
                "timestamp": now + timedelta(hours=i),
                "temp": 20.0,
                "sg": 1.050 - i * 0.002,
                "batch_id": "batch1",
                "og": 1.050,
                "fg": 1.010
            })
            
        df = pd.DataFrame(data)
        X, y_fg, y_time = prepare_features(df)
        
        self.assertEqual(len(X), 1)
        self.assertEqual(X[0][0], 1.050) # OG
        self.assertGreater(X[0][1], 0)   # Velocity
        self.assertEqual(y_fg[0], 1.010)
        self.assertGreater(y_time[0], 0)

    @patch('app.ml.prediction.load_training_data')
    def test_train_models(self, mock_load):
        from app.ml.prediction import train_models, FG_MODEL_PATH, TIME_MODEL_PATH
        
        # Create mock data for 5 batches
        now = datetime.now(timezone.utc)
        all_data = []
        for b in range(5):
            for i in range(20):
                all_data.append({
                    "timestamp": now + timedelta(hours=i),
                    "temp": 20.0 + b,
                    "sg": 1.050 - i * 0.002,
                    "batch_id": f"batch{b}",
                    "og": 1.050,
                    "fg": 1.010
                })
        
        mock_load.return_value = pd.DataFrame(all_data)
        
        # Clean up existing models
        if os.path.exists(FG_MODEL_PATH): os.remove(FG_MODEL_PATH)
        if os.path.exists(TIME_MODEL_PATH): os.remove(TIME_MODEL_PATH)
        
        result = train_models()
        
        self.assertEqual(result["status"], "success")
        self.assertTrue(os.path.exists(FG_MODEL_PATH))
        self.assertTrue(os.path.exists(TIME_MODEL_PATH))

    def test_predict_fg(self):
        from app.ml.prediction import predict_fg
        
        # Test fallback
        with patch('os.path.exists', return_value=False):
            result = predict_fg(og=1.050)
            self.assertEqual(result["method"], "formula")
            self.assertEqual(result["predicted_fg"], 1.013) # 75% attenuation

    def test_predict_time_to_fg(self):
        from app.ml.prediction import predict_time_to_fg
        
        # Test fallback
        with patch('os.path.exists', return_value=False):
            result = predict_time_to_fg(og=1.050, days_elapsed=2)
            self.assertEqual(result["method"], "formula")
            self.assertEqual(result["days_remaining"], 5)

if __name__ == '__main__':
    unittest.main()
