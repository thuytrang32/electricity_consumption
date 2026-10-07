import json
import time
from pathlib import Path

import joblib
from sqlalchemy.orm import Session

from src.api.schemas import PredictionRequest
from src.repositories.prediction_repository import PredictionRepository


class PredictionService:
    def __init__(self, repository: PredictionRepository | None = None):
        self.repository = repository or PredictionRepository()
        self.model = None
        self.pipeline = None
        self.training_metadata = {}

        backend_dir = Path(__file__).resolve().parents[2]
        self.model_path = backend_dir / "models" / "best_model.joblib"
        self.pipeline_path = backend_dir / "models" / "data_pipeline.joblib"
        self.metadata_path = backend_dir / "models" / "training_metadata.json"

    @property
    def ready(self) -> bool:
        return self.model is not None and self.pipeline is not None

    def load_artifacts(self) -> None:
        if not self.model_path.exists() or not self.pipeline_path.exists():
            raise RuntimeError(
                "Model artifacts are missing. Run `python -m src.models.train_evaluate` "
                "from the backend directory first."
            )

        self.model = joblib.load(self.model_path)
        self.pipeline = joblib.load(self.pipeline_path)

        if self.metadata_path.exists():
            with self.metadata_path.open(encoding="utf-8") as file:
                self.training_metadata = json.load(file)

    def create_prediction(self, db: Session, request: PredictionRequest):
        if not self.ready:
            raise RuntimeError("Prediction model is not loaded")

        started = time.perf_counter()
        payload = request.model_dump(mode="json")

        # Reuse exactly the same feature ordering and scaler as training.
        inference_row = self.pipeline.prepare_inference_row(payload)
        matrix = self.pipeline.scaler.transform(inference_row.values)
        prediction = float(self.model.predict(matrix)[0])
        latency_ms = (time.perf_counter() - started) * 1000

        return self.repository.create(
            db,
            prediction_date=request.date,
            forecast_j_1=request.forecast_j_1,
            forecast_j=request.forecast_j,
            lag_1d=request.lag_1d,
            lag_7d=request.lag_7d,
            lag_14d=request.lag_14d,
            prediction_mw=round(prediction, 2),
            model_used=self.model.__class__.__name__,
            latency_ms=round(latency_ms, 3),
            input_payload=payload,
        )

    def list_predictions(self, db: Session, limit: int):
        return self.repository.list_recent(db, limit)

    def get_prediction(self, db: Session, prediction_id: int):
        return self.repository.get_by_id(db, prediction_id)

    def get_model_info(self) -> dict:
        return {
            **self.training_metadata,
            "runtime_model_class": self.model.__class__.__name__ if self.model else None,
            "model_loaded": self.ready,
        }
