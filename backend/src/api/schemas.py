from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class PredictionRequest(BaseModel):
    date: date
    forecast_j_1: float = Field(default=55000.0, ge=0)
    forecast_j: float = Field(default=55000.0, ge=0)
    lag_1d: float = Field(default=55000.0, gt=0)
    lag_7d: float = Field(default=55000.0, gt=0)
    lag_14d: float = Field(default=55000.0, gt=0)
    rolling_mean_7d: float = Field(default=55000.0, gt=0)
    rolling_mean_30d: float = Field(default=55000.0, gt=0)

    fioul: float = Field(default=100.0, ge=0)
    coal: float = Field(default=50.0, ge=0)
    gas: float = Field(default=3000.0, ge=0)
    nuclear: float = Field(default=40000.0, ge=0)
    wind: float = Field(default=5000.0, ge=0)
    solar: float = Field(default=1000.0, ge=0)
    hydraulic: float = Field(default=8000.0, ge=0)
    pumping: float = -1000.0
    bioenergy: float = Field(default=1000.0, ge=0)
    physical_exchanges: float = 0.0
    co2_rate: float = Field(default=30.0, ge=0)


class PredictionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    prediction_date: date
    forecast_j_1: float
    forecast_j: float
    lag_1d: float
    lag_7d: float
    lag_14d: float
    prediction_mw: float
    model_used: str
    latency_ms: float
    created_at: datetime


class HealthResponse(BaseModel):
    status: str
    model_loaded: bool
    database: str
