from pathlib import Path
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, Response, JSONResponse
from fastapi.staticfiles import StaticFiles

from .config import MAPS_DIR, CHANGE_DIR, COLORMAP, CHANGE_COLORMAP
from .raster_tiles import tile_png
from .stats import veg_area_ha, read_summary_csv
from .jobs import start_rf_job, start_change_job, get_job

app = FastAPI(title="UGCL Dashboard API")

FRONTEND_DIR = Path(__file__).resolve().parents[1] / "frontend"
app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")


@app.get("/", response_class=HTMLResponse)
def index():
    html = (FRONTEND_DIR / "index.html").read_text(encoding="utf-8")
    return HTMLResponse(html)


@app.get("/api/years")
def years():
    years = sorted([int(p.stem.split("_")[1]) for p in MAPS_DIR.glob("rf_*.tif") if p.stem.split("_")[1].isdigit()])
    return {"years": years}


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

    # if you already generate summary_stats.csv, you can also read it:
    summary = read_summary_csv(CHANGE_DIR / "summary_stats.csv") or {}

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
    png = tile_png(tif, z, x, y, COLORMAP)
    return Response(content=png, media_type="image/png")


@app.get("/tiles/change/{y1}/{y2}/{z}/{x}/{y}.png")
def change_tiles(y1: int, y2: int, z: int, x: int, y: int):
    tif = CHANGE_DIR / f"change_{y1}_{y2}.tif"
    png = tile_png(tif, z, x, y, CHANGE_COLORMAP)
    return Response(content=png, media_type="image/png")


@app.post("/api/run/rf")
def run_rf(year: int):
    job = start_rf_job(year)
    return {"job_id": job.id, "status": job.status, "message": job.message}


@app.post("/api/run/change")
def run_change(y1: int, y2: int):
    job = start_change_job(y1, y2)
    return {"job_id": job.id, "status": job.status, "message": job.message}


@app.get("/api/job/{job_id}")
def job_status(job_id: str):
    job = get_job(job_id)
    if not job:
        return JSONResponse({"error": "Job not found"}, status_code=404)
    return {"job_id": job.id, "status": job.status, "message": job.message}
