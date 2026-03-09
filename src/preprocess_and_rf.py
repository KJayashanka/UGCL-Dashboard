import argparse
import glob
import os

import geopandas as gpd
import numpy as np
import rasterio
from rasterio.mask import mask
from rasterio.warp import reproject, Resampling
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, confusion_matrix

from config import (
    AOI_PATH, RAW_DIR, PROCESSED_DIR, OUTPUT_DIR, YEARS,
    NDVI_VEG, NDVI_WATER, SAMPLES_PER_CLASS, RF_PARAMS
)


# ---------- Helpers ----------
def find_band_paths(safe_dir: str):
    """
    Finds JP2 paths for B02,B03,B04,B08 (10m) and SCL (20m) inside a Sentinel-2 L2A SAFE.
    Works with typical SAFE structure.
    """
    # Search for granule img_data folders
    jp2s = glob.glob(os.path.join(safe_dir, "**", "*.jp2"), recursive=True)

    def pick(pattern):
        matches = [p for p in jp2s if pattern in os.path.basename(p)]
        if not matches:
            return None
        # prefer 10m for bands, 20m for SCL
        # pick the shortest path (usually correct granule)
        return sorted(matches, key=len)[0]

    b02 = pick("B02_10m")
    b03 = pick("B03_10m")
    b04 = pick("B04_10m")
    b08 = pick("B08_10m")
    scl = pick("SCL_20m")

    if not all([b02, b03, b04, b08, scl]):
        raise FileNotFoundError(
            f"Missing required bands in {safe_dir}\n"
            f"B02:{b02}\nB03:{b03}\nB04:{b04}\nB08:{b08}\nSCL:{scl}"
        )
    return b02, b03, b04, b08, scl


def load_aoi():
    gdf = gpd.read_file(AOI_PATH)
    if gdf.crs is None:
        raise ValueError("AOI has no CRS. Set it in QGIS and re-export.")
    return gdf


def clip_raster(path, aoi_gdf):
    with rasterio.open(path) as src:
        # reproject AOI to raster CRS
        aoi = aoi_gdf.to_crs(src.crs)
        out_img, out_transform = mask(src, aoi.geometry, crop=True)
        out_meta = src.meta.copy()
        out_meta.update({
            "height": out_img.shape[1],
            "width": out_img.shape[2],
            "transform": out_transform
        })
    return out_img[0], out_meta


def resample_to_match(src_arr, src_meta, target_meta, resampling=Resampling.nearest):
    """
    Resample src_arr to match target_meta grid.
    """
    dst = np.empty((target_meta["height"], target_meta["width"]), dtype=src_arr.dtype)
    reproject(
        source=src_arr,
        destination=dst,
        src_transform=src_meta["transform"],
        src_crs=src_meta["crs"],
        dst_transform=target_meta["transform"],
        dst_crs=target_meta["crs"],
        resampling=resampling
    )
    return dst


def ndvi(nir, red):
    denom = (nir + red).astype("float32")
    num = (nir - red).astype("float32")
    out = np.divide(num, denom, out=np.zeros_like(num, dtype="float32"), where=denom != 0)
    return out


def cloud_mask_from_scl(scl10):
    """
    SCL classes (common):
    3 = cloud shadow
    8 = cloud medium probability
    9 = cloud high probability
    10 = thin cirrus
    11 = snow/ice
    We'll mask these out.
    """
    bad = np.isin(scl10, [3, 8, 9, 10, 11])
    return ~bad  # True = keep


def auto_sample_points(features, labels, n_per_class, seed=42):
    """
    Randomly sample indices per class from label raster.
    labels: 0=invalid, 1=veg, 2=built, 3=water
    """
    rng = np.random.default_rng(seed)
    X_list, y_list = [], []

    for cls in [1, 2, 3]:
        idx = np.where(labels == cls)[0]
        if len(idx) < n_per_class:
            take = idx  # take all available if not enough
        else:
            take = rng.choice(idx, size=n_per_class, replace=False)
        X_list.append(features[take])
        y_list.append(np.full(len(take), cls, dtype=np.int32))

    X = np.vstack(X_list)
    y = np.concatenate(y_list)
    return X, y


# ---------- Main per-year processing ----------
def build_stack_and_labels(safe_dir, year):
    aoi = load_aoi()
    b02p, b03p, b04p, b08p, sclp = find_band_paths(safe_dir)

    # Clip 10m bands
    b02, meta10 = clip_raster(b02p, aoi)
    b03, _ = clip_raster(b03p, aoi)
    b04, _ = clip_raster(b04p, aoi)
    b08, _ = clip_raster(b08p, aoi)

    # Clip SCL (20m) then resample to 10m grid
    scl20, meta20 = clip_raster(sclp, aoi)
    scl10 = resample_to_match(scl20, meta20, meta10, resampling=Resampling.nearest)

    # Mask clouds/shadows
    keep = cloud_mask_from_scl(scl10)

    # NDVI
    nd = ndvi(b08, b04)

    # Stack features (float32)
    stack = np.stack([b02, b03, b04, b08, nd], axis=0).astype("float32")

    # Build label raster (fast weak labels)
    # Start as invalid=0
    lab = np.zeros((meta10["height"], meta10["width"]), dtype=np.uint8)

    # Water: very low NDVI (and keep mask)
    water = (nd <= NDVI_WATER) & keep

    # Vegetation: high NDVI (and keep mask)
    veg = (nd >= NDVI_VEG) & keep

    # Built-up: remaining keep pixels that are not veg/water
    built = keep & (~veg) & (~water)

    lab[veg] = 1
    lab[built] = 2
    lab[water] = 3

    # Save stack
    out_dir = os.path.join(PROCESSED_DIR, str(year))
    os.makedirs(out_dir, exist_ok=True)
    stack_path = os.path.join(out_dir, "stack.tif")
    meta_out = meta10.copy()
    meta_out.update(
        driver="GTiff",  # ✅ force GeoTIFF
        count=stack.shape[0],
        dtype="float32"
    )

    with rasterio.open(stack_path, "w", **meta_out) as dst:
        ...

        for i in range(stack.shape[0]):
            dst.write(stack[i], i + 1)

    return stack, lab, meta10, stack_path


def train_rf_for_year(stack, lab, meta, year):
    # Flatten
    bands, h, w = stack.shape
    feat = stack.reshape(bands, -1).T  # (pixels, features)
    labf = lab.reshape(-1)

    # Remove invalid
    valid = labf > 0
    feat_v = feat[valid]
    lab_v = labf[valid]

    # Sample balanced points
    X, y = auto_sample_points(feat_v, lab_v, SAMPLES_PER_CLASS, seed=42)

    # Train/test split (simple shuffle split)
    idx = np.arange(len(y))
    np.random.seed(42)
    np.random.shuffle(idx)
    split = int(0.7 * len(idx))
    tr, te = idx[:split], idx[split:]

    Xtr, ytr = X[tr], y[tr]
    Xte, yte = X[te], y[te]

    rf = RandomForestClassifier(**RF_PARAMS)
    rf.fit(Xtr, ytr)

    pred = rf.predict(Xte)
    report = classification_report(yte, pred, digits=4)
    cm = confusion_matrix(yte, pred)

    # Predict full map (only valid pixels)
    full_pred = np.zeros(h * w, dtype=np.uint8)
    full_pred[~valid] = 0
    full_pred[valid] = rf.predict(feat_v).astype(np.uint8)

    cls_map = full_pred.reshape(h, w)

    # Save map + metrics
    os.makedirs(os.path.join(OUTPUT_DIR, "maps"), exist_ok=True)
    os.makedirs(os.path.join(OUTPUT_DIR, "metrics"), exist_ok=True)

    out_map = os.path.join(OUTPUT_DIR, "maps", f"rf_{year}.tif")
    meta_out = meta.copy()
    meta_out.update(driver="GTiff", count=1, dtype="uint8")

    with rasterio.open(out_map, "w", **meta_out) as dst:
        dst.write(cls_map, 1)

    with open(os.path.join(OUTPUT_DIR, "metrics", f"rf_{year}_report.txt"), "w") as f:
        f.write(report + "\n\nConfusion Matrix:\n" + str(cm))

    return out_map


def main(selected_year=None):
    run_years = [selected_year] if selected_year else YEARS

    for year in run_years:
        safe_candidates = glob.glob(os.path.join(RAW_DIR, str(year), "*.SAFE"))
        if not safe_candidates:
            print(f"[SKIP] No SAFE found for {year} in {RAW_DIR}/{year}/")
            continue

        safe_dir = safe_candidates[0]
        print(f"\n=== {year} | Using: {os.path.basename(safe_dir)} ===")

        stack, lab, meta, _ = build_stack_and_labels(safe_dir, year)
        out_map = train_rf_for_year(stack, lab, meta, year)
        print(f"[DONE] RF map saved: {out_map}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--year", type=int, help="Run RF pipeline for a single year (e.g., 2018)")
    args = parser.parse_args()

    main(selected_year=args.year)

if __name__ == "__main__":
    main()
