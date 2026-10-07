import os
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from src.api.schemas import HealthResponse, PredictionRequest, PredictionResponse
from src.db.database import Base, engine, get_db
from src.services.prediction_service import PredictionService

prediction_service = PredictionService()


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    prediction_service.load_artifacts()
    yield


app = FastAPI(
    title="RTE/EDF Electricity Consumption Predictor",
    description=(
        "Full-stack demo API backed by a model trained on real RTE Eco2mix "
        "historical data."
    ),
    version="3.0.0",
    lifespan=lifespan,
)

origins = [
    origin.strip()
    for origin in os.getenv(
        "CORS_ORIGINS", "http://localhost:5173,http://localhost:3000"
    ).split(",")
    if origin.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", response_model=HealthResponse)
def health(db: Session = Depends(get_db)):
    database_status = "ok"
    try:
        db.execute(text("SELECT 1"))
    except SQLAlchemyError:
        database_status = "unavailable"

    healthy = prediction_service.ready and database_status == "ok"
    if not healthy:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "model_loaded": prediction_service.ready,
                "database": database_status,
            },
        )

    return HealthResponse(status="ok", model_loaded=True, database="ok")


@app.get("/ready")
def ready():
    if not prediction_service.ready:
        raise HTTPException(status_code=503, detail="Model artifacts are not loaded")
    return {"status": "ready"}


@app.get("/api/model-info")
def model_info():
    return prediction_service.get_model_info()


@app.post(
    "/api/predictions",
    response_model=PredictionResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_prediction(request: PredictionRequest, db: Session = Depends(get_db)):
    try:
        return prediction_service.create_prediction(db, request)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/predictions", response_model=list[PredictionResponse])
def list_predictions(
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    return prediction_service.list_predictions(db, limit)


@app.get("/api/predictions/{prediction_id}", response_model=PredictionResponse)
def get_prediction(prediction_id: int, db: Session = Depends(get_db)):
    prediction = prediction_service.get_prediction(db, prediction_id)
    if prediction is None:
        raise HTTPException(status_code=404, detail="Prediction not found")
    return prediction
