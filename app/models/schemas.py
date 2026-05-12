from typing import Optional
from pydantic import BaseModel, Field, model_validator

class CalibrationData(BaseModel):
    sensor_type: str = Field(default="tilt", description="Type of sensor, e.g., tilt or ispindel")
    actual_sg: float = Field(..., description="Actual specific gravity reading from a hydrometer")
    actual_temp: float = Field(default=20.0, description="Actual temperature reading")
    reported_sg: float = Field(..., description="Specific gravity reported by the device")

class TapUpdate(BaseModel):
    name: str = Field(default="Unknown", description="Name of the beer on tap")
    style: str = Field(default="N/A", description="Beer style")
    abv: float = Field(default=0.0, ge=0.0, description="Alcohol by volume limit")
    color: str = Field(default="#FFC107", description="Hex color code for the tap UI")
    keg_date: Optional[str] = Field(default=None, description="Date the keg was tapped")
    volume_remaining: float = Field(default=100.0, ge=0.0, description="Percentage of keg volume remaining")

class SettingsUpdate(BaseModel):
    """
    Settings update payload is highly dynamic. We allow extra fields but strictly type common ones.
    """
    class Config:
        extra = "allow"
    
    # Common settings that have known types
    bf_user: Optional[str] = None
    bf_key: Optional[str] = None
    serp_api_key: Optional[str] = None
    alert_telegram_token: Optional[str] = None
    alert_telegram_chat: Optional[str] = None
    batch_name: Optional[str] = None
    og: Optional[float] = None
    target_fg: Optional[float] = None
    style: Optional[str] = None
    yeast_strain: Optional[str] = None
    brew_brain_api_token: Optional[str] = None
    
    @model_validator(mode="before")
    def handle_numeric_strings(cls, values):
        if not isinstance(values, dict):
            return values
        for key in ["og", "target_fg"]:
            if key in values and isinstance(values[key], str):
                try:
                    values[key] = float(values[key])
                except ValueError:
                    pass
        return values
