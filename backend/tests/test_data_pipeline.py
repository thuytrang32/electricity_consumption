import numpy as np
import pandas as pd

from src.data.data_pipeline import DataPipeline


def make_half_hourly_fixture(days=90):
    dates = pd.date_range("2024-01-01", periods=days * 48, freq="30min")
    return pd.DataFrame(
        {
            "datetime": dates,
            "consumption": 50000 + np.sin(np.arange(len(dates)) / 10) * 1000,
            "forecast_j_1": 50000,
            "forecast_j": 50100,
            "nuclear": 40000,
            "wind": 5000,
            "solar": 1000,
            "gas": 3000,
            "hydraulic": 8000,
            "co2_rate": 30,
        }
    )


def test_aggregate_and_features():
    pipeline = DataPipeline()
    daily = pipeline.aggregate_to_daily(make_half_hourly_fixture(60))
    features = pipeline.feature_engineering(daily, is_training=True)

    assert "target_consumption_mw" in features.columns
    assert "lag_7d" in features.columns
    assert not features[pipeline.feature_cols].isnull().any().any()


def test_fit_transform_has_expected_feature_count():
    pipeline = DataPipeline()
    daily = pipeline.aggregate_to_daily(make_half_hourly_fixture(90))
    features = pipeline.feature_engineering(daily, is_training=True)

    X, y = pipeline.fit_transform_prepared(features)

    assert len(X) == len(y)
    assert X.shape[1] == len(pipeline.feature_cols)


def test_prepare_inference_row_matches_training_feature_order():
    pipeline = DataPipeline()
    row = pipeline.prepare_inference_row(
        {
            "date": "2025-01-15",
            "forecast_j_1": 55000,
            "forecast_j": 55200,
            "lag_1d": 54800,
            "lag_7d": 56000,
            "lag_14d": 55800,
            "rolling_mean_7d": 55200,
            "rolling_mean_30d": 55500,
        }
    )
    assert list(row.columns) == pipeline.feature_cols
    assert len(row) == 1


def test_real_rte_file_contract():
    from pathlib import Path

    pipeline = DataPipeline()
    data_file = (
        Path(__file__).resolve().parents[1]
        / "data"
        / "raw"
        / "eCO2mix_RTE_Annuel-Definitif_2024.xls"
    )
    frame = pipeline.load_rte_file(str(data_file))

    assert len(frame) > 10000
    assert {"datetime", "consumption", "forecast_j", "forecast_j_1"}.issubset(
        frame.columns
    )
