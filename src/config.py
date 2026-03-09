from pathlib import Path

# Project root = folder that contains "src"
BASE_DIR = Path(__file__).resolve().parent.parent

AOI_PATH = BASE_DIR / "data" / "aoi" / "colombo1.geojson"
RAW_DIR = BASE_DIR / "data" / "raw"
PROCESSED_DIR = BASE_DIR / "data" / "processed"
OUTPUT_DIR = BASE_DIR / "outputs"

YEARS = list(range(2018, 2026))  # 2018..2025

NDVI_VEG = 0.40
NDVI_WATER = 0.05
SAMPLES_PER_CLASS = 2000

RF_PARAMS = dict(
    n_estimators=400,
    random_state=42,
    n_jobs=-1,
    class_weight="balanced_subsample"
)
