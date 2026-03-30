from pathlib import Path
import argparse
import joblib
import numpy as np
import rasterio
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
PROCESSED_DIR = BASE_DIR / "data" / "processed"
OUTPUT_DIR = BASE_DIR / "outputs" / "maps"
MODEL_PATH = BASE_DIR / "models" / "rf_model_fixed.pkl"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def classify_year(year):
    stack_path = PROCESSED_DIR / str(year) / "stack.tif"
    out_map = OUTPUT_DIR / f"rf_{year}.tif"

    if not stack_path.exists():
        print(f"[SKIP] Stack not found for year {year}: {stack_path}")
        return

    print(f"\n=== Processing Year: {year} ===")
    print(f"Loading stack: {stack_path}")
    print(f"Loading model: {MODEL_PATH}")

    model = joblib.load(MODEL_PATH)

    with rasterio.open(stack_path) as src:
        stack = src.read()
        meta = src.meta.copy()

    print(f"Original stack shape: {stack.shape}")

    # 🔥 FIX: remove NDVI band
    stack = stack[:4, :, :]

    print(f"Using stack shape: {stack.shape}")

    bands, h, w = stack.shape

    X = stack.reshape(bands, -1).T
    X = pd.DataFrame(X, columns=["B02", "B03", "B04", "B08"])

    print("Running prediction...")
    y_pred = model.predict(X)

    cls_map = y_pred.reshape(h, w).astype("uint8")

    meta.update(driver="GTiff", count=1, dtype="uint8")

    with rasterio.open(out_map, "w", **meta) as dst:
        dst.write(cls_map, 1)

    print(f"[DONE] Saved classified map: {out_map}")


def classify_all_years(start_year, end_year):
    for year in range(start_year, end_year + 1):
        classify_year(year)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument("--start_year", type=int, default=2018)
    parser.add_argument("--end_year", type=int, default=2025)

    args = parser.parse_args()
    classify_all_years(args.start_year, args.end_year)