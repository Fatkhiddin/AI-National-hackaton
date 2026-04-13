# XGBoost Flat Price Models

Train two separate pipelines (repaired vs. non-repaired apartments), save them under `models/`, and run predictions either via CLI or by importing the helpers.

## Project layout
- `training_data/` – place your CSVs here (defaults: `flats_repaired.csv`, `flats_non_repaired.csv`).
- `models/` – trained model artifacts (`xgb_flat_price_repaired.joblib`, `xgb_flat_price_non_repaired.joblib`, `xgb_flat_price_bands.joblib`, `xgb_offer_classifier.joblib`).
- `train.py` – trains repaired / non-repaired models; can also train a price bands model (predicts Arzon/Bozor/Qimmat) and an offer classifier (cheap/market/expensive).
- `predict.py` – loads the right model (repaired or non-repaired) and predicts; can classify an offered price via classifier (preferred) or bands.
- `process.ipynb` – notebook version (optional).

## Requirements
- Python 3.10+ (project used 3.13)
- Dependencies: `pandas`, `numpy`, `scikit-learn`, `xgboost`, `joblib` (installed in `.venv` earlier)

## Data expectations
Columns (Uzbek → English mapping is handled in code):
- `Etaj` → floor (numeric)
- `Xonalar soni` → rooms (numeric)
- `Qurilish turi` → building_type (string)
- `Maydon(maydon eng kami sifatida)` → area (numeric, >5)
- `Bozor` → price_market (target)

## Training
- Repaired model only (default paths):
  ```bash
  python train.py --repaired-data training_data/flats_repaired.csv \
                  --repaired-model models/xgb_flat_price_repaired.joblib
  ```
- Non-repaired model (requires your non-repaired CSV):
  ```bash
  python train.py --train-non-repaired \
                  --non-repaired-data training_data/flats_non_repaired.csv \
                  --non-repaired-model models/xgb_flat_price_non_repaired.joblib
  ```
- Price bands model (predicts Arzon/Bozor/Qimmat):
  ```bash
  python train.py --train-bands \
                  --bands-data training_data/flats_repaired.csv \
                  --bands-model models/xgb_flat_price_bands.joblib
  ```
- Offer classifier (predicts cheap/market/expensive given candidate_price):
  ```bash
  python train.py --train-offer-classifier \
                  --bands-data training_data/flats_repaired.csv \
                  --offer-model models/xgb_offer_classifier.joblib
  ```
- Train both (or all three) and overwrite if they exist:
  ```bash
  python train.py --train-non-repaired --train-bands --train-offer-classifier --force
  ```
Flags: `--skip-repaired`, `--train-non-repaired`, `--train-bands`, `--train-offer-classifier`, `--force` (retrain even if model exists).

## CLI prediction
- Non-repaired (default):
  ```bash
  python predict.py --floor 1 --rooms 2 --building_type "Gʻishtli" --area 45
  ```
- Repaired model:
  ```bash
  python predict.py --repaired --floor 1 --rooms 2 --building_type "Gʻishtli" --area 45
  ```
- Classify a candidate price (uses bands model to compare Arzon/Bozor/Qimmat):
  ```bash
  python predict.py --repaired --floor 1 --rooms 2 --building_type "Gʻishtli" --area 45 \
                    --candidate-price 25000 \
                    --bands-model models/xgb_flat_price_bands.joblib
  ```
  If `xgb_offer_classifier.joblib` exists, it is used by default for classification (preferred). Override with `--offer-model` or omit to fall back to bands.
Override paths with `--repaired-model`, `--non-repaired-model`, or `--bands-model` if needed.

## Reusing in other Python projects
Import the helpers instead of using the CLI:
```python
from predict import predict_price, predict_price_bands, classify_offer, classify_offer_ml

records = [{
    "floor": 1,
    "rooms": 2,
    "building_type": "Gʻishtli",
    "area": 45,
}]
# repaired=True loads models/xgb_flat_price_repaired.joblib by default
pred = predict_price(records, repaired=True)[0]
print(pred)

bands = predict_price_bands(records)[0]
label = classify_offer(candidate_price=25000, band=bands)
print(label, bands)

label_ml, probs = classify_offer_ml(records[0], candidate_price=25000)
print(label_ml, probs)
```

If you want to train programmatically, call `train_and_save` from `train.py` with your paths and flags.

## Notes
- Models directory is created automatically when saving; place datasets in `training_data/` before training.
- Required inference features: `floor`, `rooms`, `building_type`, `area`.
