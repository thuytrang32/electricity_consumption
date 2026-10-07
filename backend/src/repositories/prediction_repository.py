from sqlalchemy import select
from sqlalchemy.orm import Session

from src.db.models import Prediction


class PredictionRepository:
    def create(self, db: Session, **values) -> Prediction:
        record = Prediction(**values)
        db.add(record)
        db.commit()
        db.refresh(record)
        return record

    def list_recent(self, db: Session, limit: int = 20) -> list[Prediction]:
        statement = select(Prediction).order_by(Prediction.id.desc()).limit(limit)
        return list(db.scalars(statement).all())

    def get_by_id(self, db: Session, prediction_id: int) -> Prediction | None:
        return db.get(Prediction, prediction_id)
