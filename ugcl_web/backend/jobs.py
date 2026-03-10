import subprocess
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Dict

BASE_DIR = Path(__file__).resolve().parents[2]
PYTHON_EXE = BASE_DIR / "venv" / "Scripts" / "python.exe"

@dataclass
class Job:
    id: str
    status: str
    message: str

JOBS: Dict[str, Job] = {}

def _run_cmd(cmd: list[str]) -> str:
    process = subprocess.run(
        cmd,
        cwd=str(BASE_DIR),
        capture_output=True,
        text=True
    )
    if process.returncode != 0:
        raise RuntimeError(process.stderr.strip() or process.stdout.strip() or "Command failed")
    return process.stdout.strip()

def start_rf_job(year: int) -> Job:
    job_id = str(uuid.uuid4())
    job = Job(id=job_id, status="running", message=f"Running RF classification for {year}...")
    JOBS[job_id] = job

    try:
        output = _run_cmd([
            str(PYTHON_EXE),
            "src/preprocess_and_rf.py",
            "--year",
            str(year)
        ])
        job.status = "done"
        job.message = output[-1000:] if output else f"RF classification completed for {year}"
    except Exception as e:
        job.status = "failed"
        job.message = str(e)

    return job

def start_change_job(y1: int, y2: int) -> Job:
    job_id = str(uuid.uuid4())
    job = Job(id=job_id, status="running", message=f"Running change detection for {y1} -> {y2}...")
    JOBS[job_id] = job

    try:
        output = _run_cmd([
            str(PYTHON_EXE),
            "src/change_detect.py",
            str(y1),
            str(y2)
        ])
        job.status = "done"
        job.message = output[-1000:] if output else f"Change detection completed for {y1} -> {y2}"
    except Exception as e:
        job.status = "failed"
        job.message = str(e)

    return job

def get_job(job_id: str):
    return JOBS.get(job_id)