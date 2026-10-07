# Electricity consumption predictor

## 1. Architecture

```text
      RTE Eco2mix files (2012 → 2026)
              │
              ▼
  cleaning → daily aggregation → features
              │
              ▼
 Decision Tree / Random Forest / KNN / RBFN
              │
              ▼
       evaluation (R²/RMSE/MAPE)
              │
              ▼
   best_model.joblib + data_pipeline.joblib

-------------------------------------------------

Browser
  │
  ▼
React frontend :3000
  │ HTTP/JSON
  ▼
FastAPI backend :8000
  │
  ├── PredictionService ──► trained model + fitted scaler
  │
  └── PredictionRepository ──► PostgreSQL
```


## 2. Data

`backend/data/raw/` contains the original RTE Eco2mix files

The current training metadata reports:

- 14 RTE files
- 246,960 cleaned half-hourly rows
- 5,145 daily rows
- period: 2012-01-01 → 2026-01-31
- chronological train/test split


## 3. Model training


```bash
cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate
# Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
python -m src.models.train_evaluate
```

Training performs:

```text
load real RTE files
  ↓
clean + aggregate to daily level
  ↓
chronological train/test split
  ↓
calendar + lag + rolling + energy-system features
  ↓
fit scaler on train only
  ↓
train 4 regressors
  ↓
compare R² / RMSE / MAPE / accuracy ±5%
  ↓
select lowest MAPE
  ↓
save model + preprocessing artifacts + metadata
```

Outputs are written to `backend/models/`.

## 4. Run the application

Prerequisite: Docker Desktop (or Docker Engine + Compose).

From the repository root:

```bash
docker compose up --build
```

Then open:

- React: `http://localhost:3000`
- FastAPI Swagger: `http://localhost:8000/docs`
- health: `http://localhost:8000/health`

The stack is:

```text
frontend container
      ↓
backend container
      ↓
PostgreSQL container
      ↓
persistent Docker volume
```

Stop it with:

```bash
docker compose down
```

To also delete the local database volume:

```bash
docker compose down -v
```

## 5. API

### Health

```http
GET /health
```

Checks both the trained model and the database connection.

### Model information

```http
GET /api/model-info
```

Returns the training metadata loaded from `backend/models/training_metadata.json`.

### Create and persist a prediction

```http
POST /api/predictions
Content-Type: application/json
```

Minimal request (other RTE-like inputs have defaults):

```json
{
  "date": "2025-01-15",
  "forecast_j_1": 55000,
  "forecast_j": 55200,
  "lag_1d": 54800,
  "lag_7d": 56000
}
```

Flow:

```text
Pydantic validation
   ↓
PredictionService
   ↓
DataPipeline.prepare_inference_row()
   ↓
saved StandardScaler
   ↓
saved RandomForest model
   ↓
prediction
   ↓
PredictionRepository
   ↓
INSERT PostgreSQL
   ↓
201 JSON response
```

### Prediction history

```http
GET /api/predictions?limit=20
```

### One prediction

```http
GET /api/predictions/{id}
```

## 6. PostgreSQL

The application stores prediction history in the `predictions` table. Important fields include:

```text
id
prediction_date
forecast_j_1
forecast_j
lag_1d
lag_7d
lag_14d
prediction_mw
model_used
latency_ms
input_payload (JSON)
created_at
```

Inspect it while Compose is running:

```bash
docker compose exec db psql -U appuser -d electricity
```

Then:

```sql
SELECT id, prediction_date, forecast_j, prediction_mw, model_used
FROM predictions
ORDER BY id DESC;
```

Exit with `\q`.

## 7. Tests

Backend tests cover:

- data aggregation and feature engineering
- inference feature ordering
- contract against a real RTE 2024 file
- API health
- model metadata
- prediction endpoint
- database persistence/history
- validation and 404 behavior

Run:

```bash
cd backend
pip install -r requirements-dev.txt
PYTHONPATH=. pytest tests -v
```

On Windows PowerShell:

```powershell
$env:PYTHONPATH="."
pytest tests -v
```

Frontend has a Vitest/Testing Library component test:

```bash
cd frontend
npm install
npm test
```

## 8. Docker

There are two Dockerfiles:

```text
backend/Dockerfile
frontend/Dockerfile
```

The frontend uses a multi-stage build:

```text
Node/Vite build
    ↓
static dist files
    ↓
Nginx runtime
```

Nginx also proxies `/api/*` and `/health` to the backend, so the browser uses one origin.

## 9. CI / Continuous Delivery

GitHub Actions is in `.github/workflows/ci_cd.yml`.

```text
push / pull request
      ↓
LINT
 ├─ Python compile + Ruff
 └─ React ESLint
      ↓
TEST
 ├─ PostgreSQL service container
 ├─ backend unit/API integration tests
 └─ frontend component tests
      ↓
BUILD
 ├─ Vite production build
 ├─ backend Docker image
 └─ frontend Docker image
      ↓
PUBLISH (main only)
 ├─ backend image → GHCR
 └─ frontend image → GHCR
```

The publish tags are:

```text
latest
<git commit SHA>
```

## 10. Continuous Deployment

`.github/workflows/deploy.yml` contains a manual deployment workflow for a Docker host. It is intentionally manual until a real deployment host and GitHub secrets are configured.

See [DEPLOYMENT.md](DEPLOYMENT.md) for the setup and for how to turn it into automatic deployment after the manual path works.

## 11. Locust load testing

Start the application first:

```bash
docker compose up --build
```

Then in another terminal:

```bash
pip install -r locust/requirements.txt
locust -f locust/locustfile.py --host http://localhost:8000
```

Open:

```text
http://localhost:8089
```

Example:

```text
Users: 50
Spawn rate: 5 users/s
```

The simulated traffic is weighted toward `POST /api/predictions`, with smaller amounts of history and health requests. Use Locust to discuss throughput, latency, percentiles and failures.

## 12. Repository structure

```text
.
├── backend/
│   ├── data/raw/                 # RTE Eco2mix files
│   ├── models/                   # trained artifacts + metadata
│   ├── src/
│   │   ├── api/                  # HTTP layer / schemas
│   │   ├── data/                 # data pipeline
│   │   ├── db/                   # SQLAlchemy setup/models
│   │   ├── models/               # training code / RBFN
│   │   ├── repositories/         # DB access
│   │   └── services/             # business/inference logic
│   ├── tests/
│   └── Dockerfile
├── frontend/                     # React + Vite + Nginx
├── locust/
├── .github/workflows/
├── docker-compose.yml
├── docker-compose.prod.yml
└── DEPLOYMENT.md
```

