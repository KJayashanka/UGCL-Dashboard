from pathlib import Path
import rasterio
import pandas as pd

from .config import VEG_CLASS


def area_ha(pixel_count: int, pixel_size_m: float) -> float:
    return (pixel_count * (pixel_size_m ** 2)) / 10000.0


def veg_area_ha(map_path: Path) -> float:
    with rasterio.open(map_path) as src:
        arr = src.read(1)
        px = abs(src.transform.a)
    veg_px = int((arr == VEG_CLASS).sum())
    return float(area_ha(veg_px, px))


def read_summary_csv(csv_path: Path):
    if not csv_path.exists():
        return None
    df = pd.read_csv(csv_path)
    if df.empty:
        return None
    return df.iloc[0].to_dict()
