from io import BytesIO
from pathlib import Path
from typing import Dict, Tuple

from rio_tiler.io import COGReader
from rio_tiler.utils import render
from fastapi import HTTPException
from PIL import Image
import numpy as np

RGBA = Tuple[int, int, int, int]


def _apply_colormap(data: np.ndarray, cmap: Dict[int, RGBA]) -> np.ndarray:
    """
    data: 2D array of class ids
    returns: 4xHxW uint8 RGBA image
    """
    h, w = data.shape
    out = np.zeros((4, h, w), dtype=np.uint8)

    for k, rgba in cmap.items():
        mask = (data == k)
        if mask.any():
            out[0][mask] = rgba[0]
            out[1][mask] = rgba[1]
            out[2][mask] = rgba[2]
            out[3][mask] = rgba[3]
    return out


def tile_png(tif_path: Path, z: int, x: int, y: int, cmap: Dict[int, RGBA]) -> bytes:
    if not tif_path.exists():
        raise HTTPException(status_code=404, detail=f"File not found: {tif_path}")

    with COGReader(str(tif_path)) as cog:
        img = cog.tile(x, y, z)  # returns ImageData
        data = img.data  # shape: (bands, H, W) or (H, W) depending
        if data.ndim == 3:
            data = data[0]  # take first band

        data = data.astype(np.int32)
        rgba = _apply_colormap(data, cmap)
        png = render(rgba, img_format="PNG")
        return png
