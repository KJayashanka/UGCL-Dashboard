from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]   # D:\IIT\FYP\UGCL
OUTPUTS = BASE_DIR / "outputs"
MAPS_DIR = OUTPUTS / "maps"
CHANGE_DIR = OUTPUTS / "change"

# Your class codes
VEG_CLASS = 1
BUILT_CLASS = 2
OTHER_CLASS = 3

# Categorical colors (RGBA) for tiles
# Feel free to adjust colors; these are readable on maps
COLORMAP = {
    0: (0, 0, 0, 0),           # transparent for NoData / background
    VEG_CLASS: (0, 160, 0, 200),    # green
    BUILT_CLASS: (200, 0, 0, 200),  # red
    OTHER_CLASS: (255, 200, 0, 200) # yellow
}

CHANGE_COLORMAP = {
    0: (0, 0, 0, 0),              # no change / background transparent
    1: (200, 0, 0, 200),          # vegetation loss (red)
    2: (0, 160, 0, 200),          # vegetation gain (green)
    3: (100, 100, 100, 120)       # optional: unchanged/other if you use it
}