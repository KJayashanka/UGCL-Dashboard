from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, Response, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .config import MAPS_DIR, CHANGE_DIR, COLORMAP, CHANGE_COLORMAP, AVAILABLE_YEARS
from .raster_tiles import tile_png
from .stats import veg_area_ha, read_summary_csv
from .jobs import start_rf_job, start_change_job, get_job

app = FastAPI(title="UGCL Dashboard API")

FRONTEND_DIR = Path(__file__).resolve().parents[1] / "frontend"
app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")


class RFRunRequest(BaseModel):
    year: int


class ChangeRunRequest(BaseModel):
    y1: int
    y2: int


@app.get("/", response_class=HTMLResponse)
def index():
    html = (FRONTEND_DIR / "index.html").read_text(encoding="utf-8")
    return HTMLResponse(html)


@app.get("/api/years")
def years():
    return {"years": AVAILABLE_YEARS}


@app.get("/api/file-status")
def file_status(year: int):
    rf_path = MAPS_DIR / f"rf_{year}.tif"
    return {
        "year": year,
        "rf_exists": rf_path.exists()
    }


@app.get("/api/change-status")
def change_status(y1: int, y2: int):
    change_path = CHANGE_DIR / f"change_{y1}_{y2}.tif"
    return {
        "y1": y1,
        "y2": y2,
        "change_exists": change_path.exists()
    }


@app.get("/api/stats")
def stats(y1: int, y2: int):
    m1 = MAPS_DIR / f"rf_{y1}.tif"
    m2 = MAPS_DIR / f"rf_{y2}.tif"

    if not m1.exists() or not m2.exists():
        return JSONResponse({"error": "RF maps not found for selected years"}, status_code=404)

    v1 = veg_area_ha(m1)
    v2 = veg_area_ha(m2)
    net = v2 - v1
    pct = (net / v1 * 100.0) if v1 > 0 else 0.0

    summary_path = CHANGE_DIR / "summary_stats.csv"
    summary = read_summary_csv(summary_path) if summary_path.exists() else {}

    return {
        "veg_y1_ha": round(v1, 2),
        "veg_y2_ha": round(v2, 2),
        "net_change_ha": round(net, 2),
        "net_change_percent": round(pct, 2),
        "summary_csv": summary
    }


@app.get("/tiles/rf/{year}/{z}/{x}/{y}.png")
def rf_tiles(year: int, z: int, x: int, y: int):
    tif = MAPS_DIR / f"rf_{year}.tif"
    if not tif.exists():
        return JSONResponse({"error": f"rf_{year}.tif not found"}, status_code=404)

    png = tile_png(tif, z, x, y, COLORMAP)
    return Response(content=png, media_type="image/png")


@app.get("/tiles/change/{y1}/{y2}/{z}/{x}/{y}.png")
def change_tiles(y1: int, y2: int, z: int, x: int, y: int):
    tif = CHANGE_DIR / f"change_{y1}_{y2}.tif"
    if not tif.exists():
        return JSONResponse({"error": f"change_{y1}_{y2}.tif not found"}, status_code=404)

    png = tile_png(tif, z, x, y, CHANGE_COLORMAP)
    return Response(content=png, media_type="image/png")


@app.post("/api/run/rf")
def run_rf(req: RFRunRequest):
    if req.year not in AVAILABLE_YEARS:
        raise HTTPException(status_code=400, detail="Unsupported year.")

    job = start_rf_job(req.year)
    return {"job_id": job.id, "status": job.status, "message": job.message}


@app.post("/api/run/change")
def run_change(req: ChangeRunRequest):
    if req.y1 not in AVAILABLE_YEARS or req.y2 not in AVAILABLE_YEARS:
        raise HTTPException(status_code=400, detail="Unsupported year selection.")
    if req.y1 == req.y2:
        raise HTTPException(status_code=400, detail="Year 1 and Year 2 must be different.")

    job = start_change_job(req.y1, req.y2)
    return {"job_id": job.id, "status": job.status, "message": job.message}


@app.get("/api/job/{job_id}")
def job_status(job_id: str):
    job = get_job(job_id)
    if not job:
        return JSONResponse({"error": "Job not found"}, status_code=404)

    return {"job_id": job.id, "status": job.status, "message": job.message}