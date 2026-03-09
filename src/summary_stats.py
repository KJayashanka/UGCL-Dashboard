import rasterio
import numpy as np
import pandas as pd
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

MAPS = ROOT / "outputs" / "maps"
CHANGE = ROOT / "outputs" / "change"

PIXEL_AREA_HA = (10 * 10) / 10000  # Sentinel-2 = 10m

CLASS_NAMES = {
    1: "Vegetation",
    2: "Built-up",
    3: "Water"
}

def area_by_class(year):
    path = MAPS / f"rf_{year}.tif"
    with rasterio.open(path) as src:
        arr = src.read(1)

    rows = []
    for cls, name in CLASS_NAMES.items():
        area = np.sum(arr == cls) * PIXEL_AREA_HA
        rows.append({
            "Year": year,
            "Class": name,
            "Area_ha": round(area, 2)
        })

    return rows

def main():
    rows = []
    for year in [2018, 2025]:
        rows.extend(area_by_class(year))

    df = pd.DataFrame(rows)
    out = CHANGE / "area_by_class.csv"
    df.to_csv(out, index=False)

    print("Saved:", out)
    print(df)

if __name__ == "__main__":
    main()
