from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]

# Fixed supported years
AVAILABLE_YEARS = [2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025]

# Paths
DATA_DIR = BASE_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"

OUTPUT_DIR = BASE_DIR / "outputs"
MAPS_DIR = OUTPUT_DIR / "maps"
CHANGE_DIR = OUTPUT_DIR / "change"
METRICS_DIR = OUTPUT_DIR / "metrics"
MODELS_DIR = BASE_DIR / "models"

# Class codes
VEG_CLASS = 1
BUILT_CLASS = 2
OTHER_CLASS = 3

# Tile colors for RF maps
COLORMAP = {
    0: (0, 0, 0, 0),              # transparent / nodata
    VEG_CLASS: (0, 160, 0, 200),  # green
    BUILT_CLASS: (200, 0, 0, 200),# red
    OTHER_CLASS: (255, 200, 0, 200) # yellow
}

# Change map colors
# adjust to your change_detect class codes if different
CHANGE_COLORMAP = {
    0: (0, 0, 0, 0),              # transparent / nodata
    1: (180, 180, 180, 120),      # stable non-veg
    2: (0, 100, 0, 180),          # stable vegetation
    3: (0, 200, 0, 220),          # gain
    4: (220, 0, 0, 220),          # loss
}