import random
from datetime import date, timedelta

from locust import HttpUser, between, task


class ElectricityPredictorUser(HttpUser):
    wait_time = between(1, 3)

    @task(8)
    def create_prediction(self):
        target_date = date(2025, 1, 15) + timedelta(days=random.randint(-30, 30))
        forecast_j = random.uniform(45000, 70000)

        payload = {
            "date": target_date.isoformat(),
            "forecast_j_1": round(forecast_j + random.normalvariate(0, 800), 1),
            "forecast_j": round(forecast_j, 1),
            "lag_1d": round(forecast_j + random.normalvariate(0, 1200), 1),
            "lag_7d": round(forecast_j + random.normalvariate(0, 1500), 1),
            "lag_14d": round(forecast_j + random.normalvariate(0, 1800), 1),
            "rolling_mean_7d": round(forecast_j + random.normalvariate(0, 1000), 1),
            "rolling_mean_30d": round(forecast_j + random.normalvariate(0, 1200), 1),
            "fioul": round(random.uniform(50, 500), 1),
            "coal": round(random.uniform(20, 400), 1),
            "gas": round(random.uniform(1500, 7000), 1),
            "nuclear": round(random.uniform(30000, 50000), 1),
            "wind": round(random.uniform(1000, 12000), 1),
            "solar": round(random.uniform(0, 8000), 1),
            "hydraulic": round(random.uniform(3000, 12000), 1),
            "pumping": round(random.uniform(-1500, 500), 1),
            "bioenergy": round(random.uniform(500, 1200), 1),
            "physical_exchanges": round(random.uniform(-8000, 8000), 1),
            "co2_rate": round(random.uniform(20, 90), 1),
        }

        with self.client.post(
            "/api/predictions", json=payload, catch_response=True
        ) as response:
            if response.status_code == 201:
                response.success()
            else:
                response.failure(f"{response.status_code}: {response.text}")

    @task(1)
    def prediction_history(self):
        self.client.get("/api/predictions?limit=20")

    @task(1)
    def health(self):
        self.client.get("/health")
