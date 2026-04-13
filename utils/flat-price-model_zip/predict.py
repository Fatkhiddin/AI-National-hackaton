from __future__ import annotations

import argparse
from pathlib import Path

import joblib
import pandas as pd

DEFAULT_REPAIRED_MODEL = Path("models/xgb_flat_price_repaired.joblib")
DEFAULT_NON_REPAIRED_MODEL = Path("models/xgb_flat_price_non_repaired.joblib")
DEFAULT_BANDS_MODEL = Path("models/xgb_flat_price_bands.joblib")
DEFAULT_OFFER_MODEL = Path("models/xgb_offer_classifier.joblib")
REQUIRED_FEATURES = ["floor", "rooms", "building_type", "area"]


def load_model(model_path: Path):
    if not model_path.exists():
        raise FileNotFoundError(f"Model file not found at {model_path}; train it first.")
    return joblib.load(model_path)


def predict_price(
    records,
    repaired: bool = True,
    repaired_model: Path = DEFAULT_REPAIRED_MODEL,
    non_repaired_model: Path = DEFAULT_NON_REPAIRED_MODEL,
):
    model_path = repaired_model if repaired else non_repaired_model
    model = load_model(model_path)

    df = pd.DataFrame(records)
    missing = set(REQUIRED_FEATURES) - set(df.columns)
    if missing:
        raise ValueError(f"Missing required feature columns: {sorted(missing)}")

    return model.predict(df)


def predict_price_bands(
    records,
    bands_model: Path = DEFAULT_BANDS_MODEL,
):
    model = load_model(bands_model)
    df = pd.DataFrame(records)
    missing = set(REQUIRED_FEATURES) - set(df.columns)
    if missing:
        raise ValueError(f"Missing required feature columns: {sorted(missing)}")
    preds = model.predict(df)
    # Return list of dicts for convenience
    result = []
    for row in preds:
        low, market, high = row
        result.append({"price_low": float(low), "price_market": float(market), "price_high": float(high)})
    return result


def classify_offer(candidate_price: float, band: dict):
    """
    Given candidate_price and predicted band dict, return label: cheap, market, expensive.
    """
    low = band["price_low"]
    market = band["price_market"]
    high = band["price_high"]
    if candidate_price <= low:
        return "cheap"
    if candidate_price >= high:
        return "expensive"
    # Between low and high: decide proximity to market
    if abs(candidate_price - market) <= max(0.05 * market, (high - low) * 0.1):
        return "market"
    return "between"


def classify_offer_ml(
    record,
    candidate_price: float,
    offer_model: Path = DEFAULT_OFFER_MODEL,
):
    """
    Use the trained classifier to label candidate price as cheap/market/expensive.
    """
    model = load_model(offer_model)
    data = {
        "floor": record["floor"],
        "rooms": record["rooms"],
        "building_type": record["building_type"],
        "area": record["area"],
        "candidate_price": candidate_price,
    }
    df = pd.DataFrame([data])
    pred_enc = model.predict(df)[0]
    probs = None
    # Map encoded label back to string if encoder is attached
    if hasattr(model, "label_encoder"):
        label = model.label_encoder.inverse_transform([int(pred_enc)])[0]
        classes = list(model.label_encoder.classes_)
    else:
        label = pred_enc
        classes = list(getattr(model, "classes_", []))

    if hasattr(model, "predict_proba"):
        prob_arr = model.predict_proba(df)[0]
        if classes and len(prob_arr) == len(classes):
            probs = {cls: float(p) for cls, p in zip(classes, prob_arr)}
        else:
            probs = None
    return label, probs


def main():
    parser = argparse.ArgumentParser(description="Predict flat price or evaluate an offer using repaired or non-repaired model.")
    parser.add_argument("--floor", type=float, required=True)
    parser.add_argument("--rooms", type=float, required=True)
    parser.add_argument("--building_type", type=str, required=True)
    parser.add_argument("--area", type=float, required=True)
    parser.add_argument(
        "--repaired",
        action="store_true",
        help="Use the repaired-apartment model (default is non-repaired)",
    )
    parser.add_argument("--repaired-model", type=Path, default=DEFAULT_REPAIRED_MODEL, help="Path to repaired model file")
    parser.add_argument(
        "--non-repaired-model",
        type=Path,
        default=DEFAULT_NON_REPAIRED_MODEL,
        help="Path to non-repaired model file",
    )
    parser.add_argument("--bands-model", type=Path, default=DEFAULT_BANDS_MODEL, help="Path to price bands model (Arzon/Bozor/Qimmat)")
    parser.add_argument("--candidate-price", type=float, help="Optional: candidate price to classify as cheap/market/expensive")
    parser.add_argument("--offer-model", type=Path, default=DEFAULT_OFFER_MODEL, help="Offer classifier model path")
    args = parser.parse_args()

    record = {
        "floor": args.floor,
        "rooms": args.rooms,
        "building_type": args.building_type,
        "area": args.area,
    }
    pred = predict_price(
        [record],
        repaired=args.repaired,
        repaired_model=args.repaired_model,
        non_repaired_model=args.non_repaired_model,
    )[0]
    print(f"Predicted market price: {pred:.2f}")

    if args.candidate_price is not None:
        # Prefer ML classifier if available; otherwise fall back to band thresholds.
        try:
            label, probs = classify_offer_ml(record, args.candidate_price, offer_model=args.offer_model)
            print(f"Offer classifier => {label}")
            if probs:
                print("Probabilities:", {k: round(v, 4) for k, v in probs.items()})
        except FileNotFoundError:
            band = predict_price_bands([record], bands_model=args.bands_model)[0]
            label = classify_offer(args.candidate_price, band)
            print(
                f"Offer assessment -> low: {band['price_low']:.2f}, market: {band['price_market']:.2f}, high: {band['price_high']:.2f}, "
                f"candidate: {args.candidate_price:.2f} => {label}"
            )


if __name__ == "__main__":
    main()
