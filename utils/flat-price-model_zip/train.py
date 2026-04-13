from __future__ import annotations

import argparse
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.metrics import mean_absolute_error, mean_squared_error
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder
from xgboost import XGBRegressor, XGBClassifier
from sklearn.preprocessing import LabelEncoder

DEFAULT_REPAIRED_DATA = Path("training_data/flats_repaired.csv")
DEFAULT_NON_REPAIRED_DATA = Path("training_data/flats_non_repaired.csv")
DEFAULT_REPAIRED_MODEL = Path("models/xgb_flat_price_repaired.joblib")
DEFAULT_NON_REPAIRED_MODEL = Path("models/xgb_flat_price_non_repaired.joblib")
DEFAULT_PRICE_BANDS_MODEL = Path("models/xgb_flat_price_bands.joblib")
DEFAULT_OFFER_CLASSIFIER_MODEL = Path("models/xgb_offer_classifier.joblib")
RANDOM_STATE = 42


def load_and_clean(data_path: Path):
    """Load CSV, rename to English-friendly columns, drop bad rows, and split features/target."""
    df = pd.read_csv(data_path)
    df = df.rename(
        columns={
            "Etaj": "floor",
            "Xonalar soni": "rooms",
            "Qurilish turi": "building_type",
            "Maydon(maydon eng kami sifatida)": "area",
            "Arzon": "price_low",
            "Bozor": "price_market",
            "Qimmat": "price_high",
        }
    )
    df = df.dropna(subset=["price_market", "floor", "rooms", "building_type", "area"])
    df = df[df["area"] > 5]
    df = df[df["price_market"] > 0]
    feature_cols = ["floor", "rooms", "building_type", "area"]
    target_col = "price_market"
    return df[feature_cols], df[target_col]


def build_pipeline():
    numeric_features = ["floor", "rooms", "area"]
    categorical_features = ["building_type"]
    preprocessor = ColumnTransformer(
        transformers=[
            ("num", "passthrough", numeric_features),
            ("cat", OneHotEncoder(handle_unknown="ignore"), categorical_features),
        ]
    )
    xgb_model = XGBRegressor(
        n_estimators=500,
        learning_rate=0.05,
        max_depth=6,
        subsample=0.8,
        colsample_bytree=0.8,
        objective="reg:squarederror",
        n_jobs=-1,
        random_state=RANDOM_STATE,
    )
    return Pipeline(steps=[("preprocessor", preprocessor), ("regressor", xgb_model)])


def _scores(y_true, y_pred):
    mae = mean_absolute_error(y_true, y_pred)
    rmse = np.sqrt(mean_squared_error(y_true, y_pred))
    return {"MAE": mae, "RMSE": rmse}


def train_and_save(data_path: Path, model_path: Path, force_retrain: bool, label: str):
    if not data_path.exists():
        print(f"Skipping {label}: data not found at {data_path}")
        return None

    if model_path.exists() and not force_retrain:
        print(f"{label} model already exists at {model_path}; use --force to retrain.")
        return None

    X, y = load_and_clean(data_path)
    X_train, X_temp, y_train, y_temp = train_test_split(
        X, y, test_size=0.3, random_state=RANDOM_STATE
    )
    X_valid, X_test, y_valid, y_test = train_test_split(
        X_temp, y_temp, test_size=0.5, random_state=RANDOM_STATE
    )

    model = build_pipeline()
    model.fit(X_train, y_train)

    metrics = {
        "validation": _scores(y_valid, model.predict(X_valid)),
        "test": _scores(y_test, model.predict(X_test)),
    }
    for split, scores in metrics.items():
        print(f"{label} {split.title()} - MAE: {scores['MAE']:.2f} | RMSE: {scores['RMSE']:.2f}")

    model_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, model_path)
    print(f"Saved {label} model to {model_path}")
    return metrics


def train_price_bands(data_path: Path, model_path: Path, force_retrain: bool):
    """
    Train a multi-output regressor to predict price_low, price_market, price_high.
    Saves a single model that returns a 3-element array per row.
    """
    if not data_path.exists():
        print(f"Skipping price bands: data not found at {data_path}")
        return None

    if model_path.exists() and not force_retrain:
        print(f"Price bands model already exists at {model_path}; use --force to retrain.")
        return None

    df = pd.read_csv(data_path)
    df = df.rename(
        columns={
            "Etaj": "floor",
            "Xonalar soni": "rooms",
            "Qurilish turi": "building_type",
            "Maydon(maydon eng kami sifatida)": "area",
            "Arzon": "price_low",
            "Bozor": "price_market",
            "Qimmat": "price_high",
        }
    )
    df = df.dropna(subset=["price_low", "price_market", "price_high", "floor", "rooms", "building_type", "area"])
    df = df[df["area"] > 5]
    df = df[(df["price_low"] > 0) & (df["price_market"] > 0) & (df["price_high"] > 0)]

    feature_cols = ["floor", "rooms", "building_type", "area"]
    target_cols = ["price_low", "price_market", "price_high"]
    X = df[feature_cols]
    y = df[target_cols]

    X_train, X_temp, y_train, y_temp = train_test_split(
        X, y, test_size=0.3, random_state=RANDOM_STATE
    )
    X_valid, X_test, y_valid, y_test = train_test_split(
        X_temp, y_temp, test_size=0.5, random_state=RANDOM_STATE
    )

    from sklearn.multioutput import MultiOutputRegressor

    base = build_pipeline()
    model = MultiOutputRegressor(base)
    model.fit(X_train, y_train)

    def _scores_multi(y_true_df, y_pred_arr):
        scores = {}
        for idx, col in enumerate(target_cols):
            scores[col] = _scores(y_true_df.iloc[:, idx], y_pred_arr[:, idx])
        return scores

    metrics = {
        "validation": _scores_multi(y_valid, model.predict(X_valid)),
        "test": _scores_multi(y_test, model.predict(X_test)),
    }
    for split, split_scores in metrics.items():
        printable = ", ".join(
            f"{col}: MAE={val['MAE']:.2f} RMSE={val['RMSE']:.2f}" for col, val in split_scores.items()
        )
        print(f"Bands {split.title()} - {printable}")

    model_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, model_path)
    print(f"Saved price bands model to {model_path}")
    return metrics


def train_offer_classifier(data_path: Path, model_path: Path, force_retrain: bool):
    """
    Train a classifier that takes features + candidate_price and predicts category: cheap/market/expensive.
    It synthesizes training samples using the provided price_low/price_market/price_high columns.
    """
    if not data_path.exists():
        print(f"Skipping offer classifier: data not found at {data_path}")
        return None

    if model_path.exists() and not force_retrain:
        print(f"Offer classifier already exists at {model_path}; use --force to retrain.")
        return None

    df = pd.read_csv(data_path)
    df = df.rename(
        columns={
            "Etaj": "floor",
            "Xonalar soni": "rooms",
            "Qurilish turi": "building_type",
            "Maydon(maydon eng kami sifatida)": "area",
            "Arzon": "price_low",
            "Bozor": "price_market",
            "Qimmat": "price_high",
        }
    )
    df = df.dropna(subset=["price_low", "price_market", "price_high", "floor", "rooms", "building_type", "area"])
    df = df[df["area"] > 5]
    df = df[(df["price_low"] > 0) & (df["price_market"] > 0) & (df["price_high"] > 0)]

    samples = []
    labels = []
    for _, row in df.iterrows():
        feats = {
            "floor": row["floor"],
            "rooms": row["rooms"],
            "building_type": row["building_type"],
            "area": row["area"],
        }
        for label, price in (("cheap", row["price_low"]), ("market", row["price_market"]), ("expensive", row["price_high"])):
            sample = dict(feats)
            sample["candidate_price"] = price
            samples.append(sample)
            labels.append(label)

    X = pd.DataFrame(samples)
    y = pd.Series(labels)
    le = LabelEncoder()
    y_enc = le.fit_transform(y)

    feature_cols_num = ["floor", "rooms", "area", "candidate_price"]
    feature_cols_cat = ["building_type"]

    preprocessor = ColumnTransformer(
        transformers=[
            ("num", "passthrough", feature_cols_num),
            ("cat", OneHotEncoder(handle_unknown="ignore"), feature_cols_cat),
        ]
    )

    clf = XGBClassifier(
        max_depth=6,
        learning_rate=0.1,
        n_estimators=400,
        subsample=0.8,
        colsample_bytree=0.8,
        objective="multi:softprob",
        eval_metric="mlogloss",
        n_jobs=-1,
        random_state=RANDOM_STATE,
    )

    model = Pipeline(steps=[("preprocessor", preprocessor), ("classifier", clf)])

    X_train, X_test, y_train, y_test = train_test_split(
        X, y_enc, test_size=0.2, random_state=RANDOM_STATE, stratify=y_enc
    )
    model.fit(X_train, y_train)

    from sklearn.metrics import accuracy_score, f1_score

    y_pred = model.predict(X_test)
    acc = accuracy_score(y_test, y_pred)
    f1 = f1_score(y_test, y_pred, average="macro")
    print(f"Offer classifier - Accuracy: {acc:.3f} | Macro F1: {f1:.3f}")

    model_path.parent.mkdir(parents=True, exist_ok=True)
    # attach encoder for later decoding
    model.label_encoder = le
    joblib.dump(model, model_path)
    print(f"Saved offer classifier to {model_path}")
    return {"accuracy": acc, "f1_macro": f1}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train repaired and non-repaired flat price models.")
    parser.add_argument("--repaired-data", type=Path, default=DEFAULT_REPAIRED_DATA, help="Path to repaired flats dataset")
    parser.add_argument("--non-repaired-data", type=Path, default=DEFAULT_NON_REPAIRED_DATA, help="Path to non-repaired flats dataset")
    parser.add_argument("--repaired-model", type=Path, default=DEFAULT_REPAIRED_MODEL, help="Where to save the repaired model (models/...)")
    parser.add_argument("--non-repaired-model", type=Path, default=DEFAULT_NON_REPAIRED_MODEL, help="Where to save the non-repaired model (models/...)")
    parser.add_argument("--bands-data", type=Path, default=DEFAULT_REPAIRED_DATA, help="Dataset to train price band model (uses Arzon/Bozor/Qimmat)")
    parser.add_argument("--bands-model", type=Path, default=DEFAULT_PRICE_BANDS_MODEL, help="Where to save the price bands model (models/...)")
    parser.add_argument("--offer-model", type=Path, default=DEFAULT_OFFER_CLASSIFIER_MODEL, help="Where to save the offer classifier model (models/...)")
    parser.add_argument("--skip-repaired", action="store_true", help="Skip training the repaired model")
    parser.add_argument("--train-non-repaired", action="store_true", help="Train the non-repaired model (requires dataset)")
    parser.add_argument("--train-bands", action="store_true", help="Train the price bands model (predicts Arzon/Bozor/Qimmat)")
    parser.add_argument("--train-offer-classifier", action="store_true", help="Train classifier that labels a candidate price as cheap/market/expensive")
    parser.add_argument("--force", action="store_true", help="Retrain even if the model file exists")
    args = parser.parse_args()

    if not args.skip_repaired:
        train_and_save(args.repaired_data, args.repaired_model, args.force, label="Repaired")

    if args.train_non_repaired:
        train_and_save(args.non_repaired_data, args.non_repaired_model, args.force, label="Non-repaired")

    if args.train_bands:
        train_price_bands(args.bands_data, args.bands_model, args.force)

    if args.train_offer_classifier:
        train_offer_classifier(args.bands_data, args.offer_model, args.force)
