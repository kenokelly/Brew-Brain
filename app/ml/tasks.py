from extensions import celery
from ml.prediction import train_models as run_training
import logging

logger = logging.getLogger("BrewBrain.Tasks")

@celery.task(name="ml.tasks.train_prediction_models")
def train_prediction_models():
    """Background task to retrain ML models."""
    logger.info("Starting background ML model training...")
    try:
        results = run_training()
        logger.info(f"ML Training Complete: {results}")
        return results
    except Exception as e:
        logger.error(f"ML Training Task Failed: {e}")
        return {"status": "error", "message": str(e)}
