from datetime import date, datetime, timezone

from sqlalchemy import JSON, Date, DateTime, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from src.db.database import Base


class Prediction(Base):
    __tablename__ = "predictions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    prediction_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    forecast_j_1: Mapped[float] = mapped_column(Float, nullable=False)
    forecast_j: Mapped[float] = mapped_column(Float, nullable=False)
    lag_1d: Mapped[float] = mapped_column(Float, nullable=False)
    lag_7d: Mapped[float] = mapped_column(Float, nullable=False)
    lag_14d: Mapped[float] = mapped_column(Float, nullable=False)
    prediction_mw: Mapped[float] = mapped_column(Float, nullable=False)
    model_used: Mapped[str] = mapped_column(String(120), nullable=False)
    latency_ms: Mapped[float] = mapped_column(Float, nullable=False)
    input_payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
