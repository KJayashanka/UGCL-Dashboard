import argparse
import os
from pathlib import Path

import numpy as np
import pandas as pd
import rasterio
from rasterio.warp import reproject, Resampling

BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = BASE_DIR / "outputs"
VEG_CLASS = 1


def area_hectares(pixel_count, pixel_size_m=10):
    return (pixel_count * (pixel_size_m ** 2)) / 10000.0


def read_aligned_arrays(ref_path, target_path):
    with rasterio.open(ref_path) as ref:
        ref_arr = ref.read(1)
        ref_meta = ref.meta.copy()

        with rasterio.open(target_path) as src:
            aligned = np.empty((ref.height, ref.width), dtype=src.dtypes[0])

            reproject(
                source=rasterio.band(src, 1),
                destination=aligned,
                src_transform=src.transform,
                src_crs=src.crs,
                dst_transform=ref.transform,
                dst_crs=ref.crs,
                resampling=Resampling.nearest
            )

    return ref_arr, aligned, ref_meta


def main(y1=2018, y2=2025):
    m1 = OUTPUT_DIR / "maps" / f"rf_{y1}.tif"
    m2 = OUTPUT_DIR / "maps" / f"rf_{y2}.tif"

    print("Looking for:", m1)
    print("Looking for:", m2)
    print(f"Exists {y1}?", m1.exists())
    print(f"Exists {y2}?", m2.exists())

    if not m1.exists() or not m2.exists():
        print(f"Missing file for {y1} or {y2}")
        return

    A, B, meta = read_aligned_arrays(str(m1), str(m2))

    with rasterio.open(str(m1)) as ref:
        pixel_size = abs(ref.transform.a)

    print("Shape of A:", A.shape)
    print("Shape of B:", B.shape)

    vegA = (A == VEG_CLASS)
    vegB = (B == VEG_CLASS)

    loss = vegA & (~vegB)
    gain = (~vegA) & vegB
    stable_veg = vegA & vegB
    stable_non = (~vegA) & (~vegB)

    change = np.zeros_like(A, dtype=np.uint8)
    change[stable_non] = 1
    change[stable_veg] = 2
    change[gain] = 3
    change[loss] = 4

    out_dir = OUTPUT_DIR / "change"
    out_dir.mkdir(parents=True, exist_ok=True)

    out_map = out_dir / f"change_{y1}_{y2}.tif"
    meta.update(dtype="uint8", count=1)

    with rasterio.open(out_map, "w", **meta) as dst:
        dst.write(change, 1)

    stats = {
        "year_from": y1,
        "year_to": y2,
        "veg_loss_pixels": int(loss.sum()),
        "veg_gain_pixels": int(gain.sum()),
        "veg_loss_ha": area_hectares(int(loss.sum()), pixel_size),
        "veg_gain_ha": area_hectares(int(gain.sum()), pixel_size),
    }

    df = pd.DataFrame([stats])
    csv_path = out_dir / f"stats_{y1}_{y2}.csv"
    df.to_csv(csv_path, index=False)

    print("Saved:", out_map)
    print("Saved:", csv_path)
    print(df)


if __name__ == "__main__":
    years = list(range(2018, 2026))  # 2018 to 2025

    for i in range(len(years)):
        for j in range(i + 1, len(years)):
            y1 = years[i]
            y2 = years[j]

            print(f"\nProcessing {y1} → {y2}")
            main(y1, y2)