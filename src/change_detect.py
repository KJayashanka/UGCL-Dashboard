# src/change_detect.py
import os
from pathlib import Path
import numpy as np
import pandas as pd
import rasterio

BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = BASE_DIR / "outputs"
VEG_CLASS = 1

def area_hectares(pixel_count, pixel_size_m=10):
    # area = n * (pixel_size^2) ; convert m2 -> hectares (1 ha = 10,000 m2)
    return (pixel_count * (pixel_size_m ** 2)) / 10000.0


def main(y1=2018, y2=2025):
    m1 = OUTPUT_DIR / "maps" / f"rf_{y1}.tif"
    m2 = OUTPUT_DIR / "maps" / f"rf_{y2}.tif"

    print("Looking for:", m1)
    print("Looking for:", m2)
    print("Exists 2018?", m1.exists())
    print("Exists 2025?", m2.exists())

    with rasterio.open(str(m1)) as a, rasterio.open(str(m2)) as b:
        A = a.read(1)
        B = b.read(1)
        meta = a.meta.copy()
        pixel_size = a.transform.a  # usually 10

    vegA = (A == VEG_CLASS)
    vegB = (B == VEG_CLASS)

    loss = vegA & (~vegB)
    gain = (~vegA) & vegB
    stable_veg = vegA & vegB
    stable_non = (~vegA) & (~vegB)

    # encode change map
    # 0=no-data/other, 1=stable non-veg, 2=stable veg, 3=gain, 4=loss
    change = np.zeros_like(A, dtype=np.uint8)
    change[stable_non] = 1
    change[stable_veg] = 2
    change[gain] = 3
    change[loss] = 4

    os.makedirs(os.path.join(OUTPUT_DIR, "change"), exist_ok=True)
    out_map = os.path.join(OUTPUT_DIR, "change", f"change_{y1}_{y2}.tif")

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
    df.to_csv(os.path.join(OUTPUT_DIR, "change", f"stats_{y1}_{y2}.csv"), index=False)

    print("Saved:", out_map)
    print(df)


if __name__ == "__main__":
    main(2018, 2025)
