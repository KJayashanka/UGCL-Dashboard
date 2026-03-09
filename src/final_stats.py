from pathlib import Path
import numpy as np
import pandas as pd
import rasterio

VEG_CLASS = 1

def area_ha(n, pixel_size=10):
    return (n * (pixel_size ** 2)) / 10000

def veg_area(map_path: Path):
    with rasterio.open(str(map_path)) as src:
        arr = src.read(1)
        px = abs(src.transform.a)
    veg = int((arr == VEG_CLASS).sum())
    return veg, area_ha(veg, px)

def main():
    BASE_DIR = Path(__file__).resolve().parent.parent  # D:\IIT\FYP\UGCL

    m2018 = BASE_DIR / "outputs" / "maps" / "rf_2018.tif"
    m2025 = BASE_DIR / "outputs" / "maps" / "rf_2025.tif"

    print("BASE_DIR =", BASE_DIR)
    print("Looking for 2018:", m2018)
    print("Looking for 2025:", m2025)
    print("Exists 2018?", m2018.exists())
    print("Exists 2025?", m2025.exists())

    if not m2018.exists():
        raise FileNotFoundError(f"Missing file: {m2018}")
    if not m2025.exists():
        raise FileNotFoundError(f"Missing file: {m2025}")

    v18_pix, v18_ha = veg_area(m2018)
    v25_pix, v25_ha = veg_area(m2025)

    net = v25_ha - v18_ha
    pct = (net / v18_ha) * 100 if v18_ha > 0 else 0

    df = pd.DataFrame([{
        "veg_2018_pixels": v18_pix,
        "veg_2018_ha": round(v18_ha, 2),
        "veg_2025_pixels": v25_pix,
        "veg_2025_ha": round(v25_ha, 2),
        "net_change_ha": round(net, 2),
        "net_change_percent_vs_2018": round(pct, 2)
    }])

    out_dir = BASE_DIR / "outputs" / "change"
    out_dir.mkdir(parents=True, exist_ok=True)

    out = out_dir / "summary_stats.csv"
    df.to_csv(out, index=False)

    print("\nSummary:")
    print(df)
    print("\nSaved:", out)

if __name__ == "__main__":
    main()
