from pathlib import Path
import numpy as np
import pandas as pd
import rasterio

BASE_DIR = Path(__file__).resolve().parent.parent
PROCESSED_DIR = BASE_DIR / "data" / "processed"
EXPORT_DIR = BASE_DIR / "data" / "exports_for_colab"
EXPORT_DIR.mkdir(parents=True, exist_ok=True)

NDVI_VEG = 0.40
NDVI_WATER = 0.05
SAMPLES_PER_CLASS = 5000

def auto_sample_points(features, labels, n_per_class, seed=42):
    rng = np.random.default_rng(seed)
    X_list, y_list = [], []

    for cls in [1, 2, 3]:
        idx = np.where(labels == cls)[0]
        if len(idx) == 0:
            continue
        if len(idx) < n_per_class:
            take = idx
        else:
            take = rng.choice(idx, size=n_per_class, replace=False)

        X_list.append(features[take])
        y_list.append(np.full(len(take), cls, dtype=np.int32))

    X = np.vstack(X_list)
    y = np.concatenate(y_list)
    return X, y

def main(year=2024):
    stack_path = PROCESSED_DIR / str(year) / "stack.tif"

    with rasterio.open(stack_path) as src:
        stack = src.read()  # shape: (bands, h, w)

    bands, h, w = stack.shape
    feat = stack.reshape(bands, -1).T  # (pixels, features)

    # expected band order: B02, B03, B04, B08, NDVI
    ndvi = feat[:, 4]

    # create weak labels
    labels = np.zeros(feat.shape[0], dtype=np.uint8)
    water = ndvi <= NDVI_WATER
    veg = ndvi >= NDVI_VEG
    built = (~veg) & (~water)

    labels[veg] = 1
    labels[built] = 2
    labels[water] = 3

    valid = labels > 0
    feat_v = feat[valid]
    labels_v = labels[valid]

    X, y = auto_sample_points(feat_v, labels_v, SAMPLES_PER_CLASS)

    df = pd.DataFrame(X, columns=["B02", "B03", "B04", "B08", "NDVI"])
    df["label"] = y

    out_path = EXPORT_DIR / f"training_samples_{year}.csv"
    df.to_csv(out_path, index=False)

    print("Saved:", out_path)
    print(df.head())
    print(df["label"].value_counts())

if __name__ == "__main__":
    main(2024)