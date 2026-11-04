"""
Pydantic schemas for Advanced ML Fermentation Modeling.

Defines feature structures for yeast pitch kinetics, hop creep analysis,
batch ML training features, and prediction output payloads.
"""

from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class YeastPitchDetails(BaseModel):
    """Metadata for yeast pitching rate, viability, and propagation."""
    cells_pitch_billions: float = Field(..., description="Total yeast cells pitched in billions", ge=0.0)
    viability_percent: float = Field(default=95.0, description="Estimated viability percentage at pitch time", ge=0.0, le=100.0)
    yeast_age_days: int = Field(default=0, description="Age of yeast package in days since manufacture or harvest", ge=0)
    generation: int = Field(default=1, description="Yeast generation number (repitch count)", ge=1)
    is_starter: bool = Field(default=False, description="Whether a yeast starter was prepared")
    starter_volume_liters: float = Field(default=0.0, description="Volume of yeast starter in liters", ge=0.0)
    starter_steps: int = Field(default=0, description="Number of propagation steps in the starter", ge=0)


class DryHopAddition(BaseModel):
    """Metadata for dry-hop additions to predict enzymatic hop creep."""
    addition_time_hours: float = Field(..., description="Hours elapsed from pitch before dry hops are added", ge=0.0)
    dosage_g_l: float = Field(..., description="Dry-hop dosage rate in grams per liter", ge=0.0)
    temperature_c: float = Field(..., description="Wort temperature during dry-hop contact time", ge=-5.0, le=35.0)
    hop_variety: str = Field(..., description="Hop variety name for enzymatic activity lookup")
    contact_time_hours: Optional[float] = Field(default=72.0, description="Target contact time in hours", ge=0.0)


class BatchMLFeatures(BaseModel):
    """Combined feature payload for training and batch ML validation."""
    batch_id: str = Field(..., description="Unique batch identifier")
    batch_name: str = Field(..., description="Name of the batch")
    style: str = Field(default="Unknown", description="Beer style code or name")
    yeast_strain: str = Field(default="Unknown", description="Yeast strain identifier")
    og: float = Field(..., description="Original Gravity", ge=1.000, le=1.200)
    fg: Optional[float] = Field(None, description="Actual Final Gravity (known after completion)", ge=0.980, le=1.100)
    pitch_details: Optional[YeastPitchDetails] = Field(default=None, description="Yeast Pitch metadata")
    dry_hop_additions: List[DryHopAddition] = Field(default_factory=list, description="Array of dry-hop additions")


class MLTrainingResponse(BaseModel):
    """Response payload detailing results of ML model training updates."""
    status: str = Field(..., description="Execution status ('success' or 'error')")
    batches_used: int = Field(..., description="Total unique batches incorporated in the model")
    trained_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat(), description="Timestamp of model training completion")
    fg_mae: float = Field(..., description="Mean Absolute Error for Final Gravity model")
    time_mae_days: float = Field(..., description="Mean Absolute Error for Time-to-FG model in days")
    features_importance: Dict[str, float] = Field(..., description="Dictionary mapping features to relative importances")


class PredictionOutputSchema(BaseModel):
    """Structure returned by ML prediction queries."""
    batch_id: str = Field(..., description="Identifier of predicted batch")
    predicted_fg: float = Field(..., description="Predicted Final Gravity value")
    predicted_fg_lower_bound: float = Field(..., description="Lower 95% confidence interval SG value")
    predicted_fg_upper_bound: float = Field(..., description="Upper 95% confidence interval SG value")
    days_to_fg: float = Field(..., description="Estimated remaining days until final gravity is reached")
    hop_creep_detected: bool = Field(default=False, description="Indicates if a hop creep signature has altered the prediction")
    hop_creep_gravity_offset: float = Field(default=0.0, description="Gravity offset applied due to expected hop creep")
    correlation_score: float = Field(default=1.0, description="Cross-correlation score against top peer batch")
    peer_batch_id: Optional[str] = Field(None, description="ID of the historically matched batch used for reference kinetics")
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat(), description="Time of prediction calculation")
