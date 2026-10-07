import json
import os
import time
import joblib
import numpy as np
import pandas as pd
from sklearn.tree import DecisionTreeRegressor
from sklearn.ensemble import RandomForestRegressor
from sklearn.neighbors import KNeighborsRegressor
from sklearn.metrics import r2_score, mean_squared_error, mean_absolute_percentage_error
from src.data.data_pipeline import DataPipeline
from src.models.custom_rbfn import RadialBasisFunctionNetwork


DATA_DIR = os.environ.get("MSPR_RTE_DATA_DIR", "data/raw")
TEST_RATIO = float(os.environ.get("MSPR_TEST_RATIO", "0.20"))


def calculate_accuracy_5pct(y_true, y_pred):
    # percentage of predictions with error <= 5%.
    y_true = np.asarray(y_true)
    y_pred = np.asarray(y_pred)
    non_zero = y_true != 0
    pct_errors = np.abs((y_true[non_zero] - y_pred[non_zero]) / y_true[non_zero])
    return float(np.mean(pct_errors <= 0.05))


def main():
    os.makedirs("models", exist_ok=True)
    os.makedirs("docs", exist_ok=True)
    pipeline = DataPipeline()

    # Load real RTE files
    raw_df = pipeline.load_rte_folder(DATA_DIR)
    print(f"Raw RTE rows after cleaning: {len(raw_df)}")
    print(f"Raw period: {raw_df['datetime'].min()} -> {raw_df['datetime'].max()}")

    # Aggregate to daily level because the subject asks for daily consumption prediction
    daily_df = pipeline.aggregate_to_daily(raw_df)
    print(f"Daily rows: {len(daily_df)}")
    print(f"Daily period: {daily_df['date'].min()} -> {daily_df['date'].max()}")

    # Feature engineering
    prepared_df = pipeline.feature_engineering(daily_df, is_training=True)
    print(f"Rows after feature engineering: {len(prepared_df)}")
    print(f"Target: {pipeline.target_col}")
    print(f"Features: {pipeline.feature_cols}")

    # Chronological split to avoid data leakage
    split_idx = int(len(prepared_df) * (1 - TEST_RATIO))
    train_df = prepared_df.iloc[:split_idx].copy()
    test_df = prepared_df.iloc[split_idx:].copy()

    print(f"Train size: {len(train_df)} | Test size: {len(test_df)}")
    print(f"Train period: {train_df['date'].min()} -> {train_df['date'].max()}")
    print(f"Test period: {test_df['date'].min()} -> {test_df['date'].max()}")

    X_train, y_train = pipeline.fit_transform_prepared(train_df)
    X_test = pipeline.transform_prepared(test_df)
    y_test = test_df[pipeline.target_col].values

    models = {
        "DecisionTree": DecisionTreeRegressor(
            max_depth=8, min_samples_leaf=5, random_state=42
        ),
        "RandomForest": RandomForestRegressor(
            n_estimators=150,
            max_depth=14,
            min_samples_leaf=3,
            random_state=42,
            n_jobs=-1,
        ),
        "KNeighbors": KNeighborsRegressor(
            n_neighbors=7, weights="distance", metric="euclidean"
        ),
        "RBFN": RadialBasisFunctionNetwork(
            n_centers=40, gamma="scale", alpha=0.1, random_state=42
        ),
    }

    results = {}
    trained_models = {}
    predictions_by_model = {}

    best_mape = float("inf")
    best_model_name = None

    for name, model in models.items():
        print(f"Training {name}...")
        start_time = time.time()

        model.fit(X_train, y_train)
        train_time = time.time() - start_time

        y_pred = model.predict(X_test)

        r2 = float(r2_score(y_test, y_pred))
        rmse = float(np.sqrt(mean_squared_error(y_test, y_pred)))
        mape = float(mean_absolute_percentage_error(y_test, y_pred))
        accuracy_5 = calculate_accuracy_5pct(y_test, y_pred)

        print(
            f"[{name}] R2={r2:.4f} | RMSE={rmse:.1f} MW | "
            f"MAPE={mape*100:.2f}% | Accuracy±5%={accuracy_5*100:.2f}% | "
            f"Train={train_time:.3f}s"
        )

        results[name] = {
            "R2": r2,
            "RMSE_MW": rmse,
            "MAPE": mape,
            "Accuracy_5pct": accuracy_5,
            "Train_Time_sec": train_time,
        }

        trained_models[name] = model
        predictions_by_model[name] = y_pred

        if mape < best_mape:
            best_mape = mape
            best_model_name = name

    print(
        f"\n--- Best Model Selection: {best_model_name} (MAPE: {best_mape*100:.2f}%) ---"
    )

    # Save artifacts
    joblib.dump(trained_models[best_model_name], "models/best_model.joblib")
    joblib.dump(pipeline, "models/data_pipeline.joblib")

    with open("models/mlflow_logs.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=4, ensure_ascii=False)

    metadata = {
        "data_source": pipeline.data_source_,
        "raw_rows_after_cleaning": int(len(raw_df)),
        "daily_rows": int(len(daily_df)),
        "rows_after_feature_engineering": int(len(prepared_df)),
        "period_start": str(daily_df["date"].min()),
        "period_end": str(daily_df["date"].max()),
        "target": pipeline.target_col,
        "target_definition": "Daily average electricity consumption in MW",
        "temperature_used": False,
        "split_type": "chronological",
        "train_rows": int(len(train_df)),
        "test_rows": int(len(test_df)),
        "best_model": best_model_name,
        "features": pipeline.feature_cols,
    }

    with open("models/training_metadata.json", "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=4, ensure_ascii=False)

    pred_df = pd.DataFrame(
        {
            "date": test_df["date"].values,
            "y_true_mw": y_test,
            "y_pred_mw": predictions_by_model[best_model_name],
            "absolute_error_mw": np.abs(y_test - predictions_by_model[best_model_name]),
            "absolute_percentage_error": np.abs(
                (y_test - predictions_by_model[best_model_name]) / y_test
            ),
        }
    )
    pred_df.to_csv("models/test_predictions.csv", index=False)

    # Generate report
    report_path = "docs/model_performance_report.md"

    report = f"""# Rapport de Performance des Modèles d'IA (RTE/EDF)

Ce document présente l'évaluation comparative des modèles entraînés sur les fichiers réels RTE Eco2mix.

## Données utilisées

* **Source :** fichiers RTE Eco2mix annuels définitifs + fichier consolidé, placés dans `{DATA_DIR}`.
* **Période :** {daily_df['date'].min()} → {daily_df['date'].max()}.
* **Données brutes après nettoyage :** {len(raw_df)} lignes demi-horaires.
* **Données d'entraînement :** {len(daily_df)} lignes journalières.
* **Cible :** consommation électrique moyenne journalière en MW (`{pipeline.target_col}`).
* **Température :** non utilisée, car elle n'est pas disponible dans les fichiers RTE fournis.
* **Variables d'entrée :** prévisions RTE J-1/J, variables calendaires, lags de consommation, moyennes glissantes, mix énergétique et taux de CO2.
* **Split :** séparation chronologique 80% entraînement / 20% test pour éviter la fuite de données futures.

## Résultats comparatifs

| Modèle | R² Score | RMSE (MW) | MAPE | Accuracy (±5%) | Temps d'entraînement |
| :--- | :---: | :---: | :---: | :---: | :---: |
"""

    for name, metrics in results.items():
        champion = " **(Champion)**" if name == best_model_name else ""
        report += (
            f"| **{name}**{champion} | {metrics['R2']:.4f} | {metrics['RMSE_MW']:.1f} | "
            f"{metrics['MAPE']*100:.2f}% | {metrics['Accuracy_5pct']*100:.2f}% | "
            f"{metrics['Train_Time_sec']:.3f} s |\n"
        )

    report += f"""

## Choix du modèle champion

Le modèle sélectionné est **{best_model_name}**, car il obtient le plus faible MAPE sur le jeu de test chronologique.

Le choix est fondé sur :
1. **MAPE**, pour mesurer l'erreur moyenne en pourcentage.
2. **RMSE**, pour mesurer l'erreur moyenne en MW.
3. **R²**, pour mesurer la capacité d'explication du modèle.
4. **Accuracy ±5%**, pour mesurer la proportion de prédictions dans un seuil métier acceptable.
5. **Temps d'entraînement**, pour vérifier la faisabilité du ré-entraînement.

## Artéfacts produits

* `models/best_model.joblib` : modèle champion.
* `models/data_pipeline.joblib` : pipeline de transformation.
* `models/mlflow_logs.json` : métriques des modèles.
* `models/training_metadata.json` : contexte d'entraînement.
* `models/test_predictions.csv` : prédictions sur le jeu de test.

"""

    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)

    print("Saved models/best_model.joblib")
    print("Saved models/data_pipeline.joblib")
    print("Saved models/mlflow_logs.json")
    print("Saved models/training_metadata.json")
    print("Saved models/test_predictions.csv")
    print("Saved docs/model_performance_report.md")
    print("--- Training completed successfully ---")


if __name__ == "__main__":
    main()
