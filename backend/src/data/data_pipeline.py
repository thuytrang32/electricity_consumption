import glob
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler

try:
    import holidays

    HAS_HOLIDAYS = True
except ImportError:
    HAS_HOLIDAYS = False


class DataPipeline:
    def __init__(self):
        self.scaler = None
        self.target_col = "target_consumption_mw"
        self.production_cols = [
            "fioul",
            "coal",
            "gas",
            "nuclear",
            "wind",
            "solar",
            "hydraulic",
            "pumping",
            "bioenergy",
            "physical_exchanges",
            "co2_rate",
        ]

        self.feature_cols = [
            # RTE forecast variables
            "forecast_j_1",
            "forecast_j",
            # Calendar variables
            "day_of_week",
            "is_weekend",
            "is_holiday",
            "month_sin",
            "month_cos",
            "day_of_year_sin",
            "day_of_year_cos",
            # Historical consumption variables
            "lag_1d",
            "lag_7d",
            "lag_14d",
            "rolling_mean_7d",
            "rolling_mean_30d",
            # Production / system context from RTE
            "fioul",
            "coal",
            "gas",
            "nuclear",
            "wind",
            "solar",
            "hydraulic",
            "pumping",
            "bioenergy",
            "physical_exchanges",
            "co2_rate",
        ]

        self.data_source_ = None
        self.raw_rows_ = 0
        self.daily_rows_ = 0

    def load_rte_file(self, file_path: str) -> pd.DataFrame:
        # Load one RTE Eco2mix file.
        df = pd.read_csv(
            file_path,
            sep="\t",
            encoding="latin1",
            index_col=False,
            low_memory=False,
        )

        required_cols = ["Date", "Heures", "Consommation"]
        missing = [c for c in required_cols if c not in df.columns]
        if missing:
            raise ValueError(f"Missing columns in {file_path}: {missing}")

        # Build datetime
        df["datetime"] = pd.to_datetime(
            df["Date"].astype(str) + " " + df["Heures"].astype(str),
            errors="coerce",
        )

        rename_map = {
            "Consommation": "consumption",
            "Prévision J-1": "forecast_j_1",
            "Prévision J": "forecast_j",
            "Fioul": "fioul",
            "Charbon": "coal",
            "Gaz": "gas",
            "Nucléaire": "nuclear",
            "Eolien": "wind",
            "Solaire": "solar",
            "Hydraulique": "hydraulic",
            "Pompage": "pumping",
            "Bioénergies": "bioenergy",
            "Ech. physiques": "physical_exchanges",
            "Taux de Co2": "co2_rate",
        }

        df = df.rename(columns=rename_map)

        keep_cols = [
            "datetime",
            "consumption",
            "forecast_j_1",
            "forecast_j",
            "fioul",
            "coal",
            "gas",
            "nuclear",
            "wind",
            "solar",
            "hydraulic",
            "pumping",
            "bioenergy",
            "physical_exchanges",
            "co2_rate",
        ]
        keep_cols = [c for c in keep_cols if c in df.columns]
        df = df[keep_cols].copy()

        for col in df.columns:
            if col != "datetime":
                df[col] = pd.to_numeric(df[col], errors="coerce")

        # 15-minute rows often have empty consumption, so we remove them.
        df = df.dropna(subset=["datetime", "consumption"])
        df = (
            df.sort_values("datetime")
            .drop_duplicates("datetime")
            .reset_index(drop=True)
        )
        return df

    def load_rte_folder(self, data_dir: str = "data/raw") -> pd.DataFrame:
        # Load all RTE files from data/raw.
        patterns = [
            str(Path(data_dir) / "eCO2mix_RTE_Annuel-Definitif_*.xls"),
            str(Path(data_dir) / "eCO2mix_RTE_En-cours-Consolide*.xls"),
        ]

        files = []
        for pattern in patterns:
            files.extend(glob.glob(pattern))

        files = sorted(set(files))

        if not files:
            raise FileNotFoundError(
                f"No RTE Eco2mix files found in {data_dir}. "
                "Expected files such as eCO2mix_RTE_Annuel-Definitif_2024.xls"
            )

        frames = []
        for file_path in files:
            print(f"Loading RTE file: {file_path}")
            frames.append(self.load_rte_file(file_path))

        raw_df = pd.concat(frames, ignore_index=True)
        raw_df = (
            raw_df.sort_values("datetime")
            .drop_duplicates("datetime")
            .reset_index(drop=True)
        )

        self.data_source_ = f"RTE Eco2mix folder: {data_dir} ({len(files)} files)"
        self.raw_rows_ = len(raw_df)
        return raw_df

    def aggregate_to_daily(self, raw_df: pd.DataFrame) -> pd.DataFrame:
        df = raw_df.copy()
        df["date"] = pd.to_datetime(df["datetime"]).dt.date
        df["date"] = pd.to_datetime(df["date"])

        # Ensure all expected columns exist
        for col in ["forecast_j_1", "forecast_j"] + self.production_cols:
            if col not in df.columns:
                df[col] = np.nan

        aggregation = {
            "consumption": ["mean", lambda s: s.sum() * 0.5],
            "forecast_j_1": "mean",
            "forecast_j": "mean",
        }

        for col in self.production_cols:
            aggregation[col] = "mean"

        daily = df.groupby("date").agg(aggregation).reset_index()

        # Flatten columns
        daily.columns = [
            "date",
            "target_consumption_mw",
            "daily_energy_mwh",
            "forecast_j_1",
            "forecast_j",
        ] + self.production_cols

        # Fill missing optional variables with robust values
        numeric_cols = [c for c in daily.columns if c != "date"]
        for col in numeric_cols:
            daily[col] = pd.to_numeric(daily[col], errors="coerce")
            daily[col] = daily[col].ffill().bfill()

            if daily[col].isna().all():
                daily[col] = 0.0
            elif daily[col].isna().any():
                daily[col] = daily[col].fillna(daily[col].median())

            daily[col] = daily[col].fillna(0.0)

        self.daily_rows_ = len(daily)
        return daily.sort_values("date").reset_index(drop=True)

    def feature_engineering(
        self, daily_df: pd.DataFrame, is_training: bool = True
    ) -> pd.DataFrame:
        df = daily_df.copy()
        df["date"] = pd.to_datetime(df["date"])
        df = df.sort_values("date").reset_index(drop=True)

        # Calendar variables
        df["day_of_week"] = df["date"].dt.dayofweek
        df["is_weekend"] = (df["day_of_week"] >= 5).astype(int)

        if HAS_HOLIDAYS:
            fr_holidays = holidays.France()
            df["is_holiday"] = df["date"].dt.date.apply(lambda d: int(d in fr_holidays))
        else:
            fixed_holidays = {
                (1, 1),
                (5, 1),
                (5, 8),
                (7, 14),
                (8, 15),
                (11, 1),
                (11, 11),
                (12, 25),
            }
            df["is_holiday"] = df["date"].apply(
                lambda d: int((d.month, d.day) in fixed_holidays)
            )

        month = df["date"].dt.month
        day_of_year = df["date"].dt.dayofyear

        df["month_sin"] = np.sin(2 * np.pi * month / 12)
        df["month_cos"] = np.cos(2 * np.pi * month / 12)
        df["day_of_year_sin"] = np.sin(2 * np.pi * day_of_year / 365.25)
        df["day_of_year_cos"] = np.cos(2 * np.pi * day_of_year / 365.25)

        # Historical consumption features
        df["lag_1d"] = df[self.target_col].shift(1)
        df["lag_7d"] = df[self.target_col].shift(7)
        df["lag_14d"] = df[self.target_col].shift(14)
        df["rolling_mean_7d"] = df[self.target_col].shift(1).rolling(7).mean()
        df["rolling_mean_30d"] = df[self.target_col].shift(1).rolling(30).mean()

        for col in self.feature_cols + [self.target_col]:
            if col not in df.columns:
                df[col] = np.nan
            df[col] = pd.to_numeric(df[col], errors="coerce")
            df[col] = df[col].ffill().bfill()

        if is_training:
            df = df.dropna(subset=self.feature_cols + [self.target_col])
        else:
            for col in self.feature_cols:
                df[col] = df[col].fillna(0.0)

        return df.reset_index(drop=True)

    def fit_transform_prepared(self, prepared_train_df: pd.DataFrame):
        # Fit scaler on train data only.
        X = prepared_train_df[self.feature_cols].values
        y = prepared_train_df[self.target_col].values

        self.scaler = StandardScaler()
        X_scaled = self.scaler.fit_transform(X)
        return X_scaled, y

    def transform_prepared(self, prepared_df: pd.DataFrame):
        # Transform features using the scaler fitted on train data.

        if self.scaler is None:
            raise ValueError("Scaler is not fitted. Call fit_transform_prepared first.")

        X = prepared_df[self.feature_cols].values
        return self.scaler.transform(X)

    def prepare_inference_row(self, payload: dict) -> pd.DataFrame:
        row = {col: payload.get(col, np.nan) for col in self.feature_cols}
        date_value = pd.to_datetime(payload.get("date"), errors="coerce")

        if pd.isna(date_value):
            raise ValueError("Invalid date format. Expected YYYY-MM-DD.")

        row["day_of_week"] = date_value.dayofweek
        row["is_weekend"] = int(date_value.dayofweek >= 5)

        if HAS_HOLIDAYS:
            row["is_holiday"] = int(date_value.date() in holidays.France())
        else:
            row["is_holiday"] = 0

        row["month_sin"] = np.sin(2 * np.pi * date_value.month / 12)
        row["month_cos"] = np.cos(2 * np.pi * date_value.month / 12)
        row["day_of_year_sin"] = np.sin(2 * np.pi * date_value.dayofyear / 365.25)
        row["day_of_year_cos"] = np.cos(2 * np.pi * date_value.dayofyear / 365.25)

        for col in self.feature_cols:
            if pd.isna(row.get(col)):
                row[col] = 0.0

        return pd.DataFrame([row])[self.feature_cols]
