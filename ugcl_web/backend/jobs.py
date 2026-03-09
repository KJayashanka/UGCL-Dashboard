import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Dict
import uuid

from .config import BASE_DIR


@dataclass
class Job:
    id: str
    status: str  # queued/running/done/failed
    message: str


JOBS: Dict[str, Job] = {}


def _run_cmd(cmd: list[str]) -> str:
    p = subprocess.run(cmd, cwd=str(BASE_DIR), capture_output=True, text=True)
    if p.returncode != 0:
        raise RuntimeError(p.stderr.strip() or "Command failed")
    return p.stdout


def start_rf_job(year: int) -> Job:
    jid = str(uuid.uuid4())
    job = Job(id=jid, status="running", message="Starting RF classification...")
    JOBS[jid] = job

    try:
        # IMPORTANT: Adjust args to match your script.
        # If your preprocess_and_rf.py runs for one year based on args, use this:
        out = _run_cmd([str(BASE_DIR / "venv/Scripts/python.exe"), "src/preprocess_and_rf.py", "--year", str(year)])

        job.status = "done"
        job.message = out[-500:]  # last part
    except Exception as e:
        job.status = "failed"
        job.message = str(e)

    return job


def start_change_job(year_from: int, year_to: int) -> Job:
    jid = str(uuid.uuid4())
    job = Job(id=jid, status="running", message="Starting change detection...")
    JOBS[jid] = job

    try:
        out = _run_cmd(
            [str(BASE_DIR / "venv/Scripts/python.exe"), "src/change_detect.py", str(year_from), str(year_to)])
        job.status = "done"
        job.message = out[-500:]
    except Exception as e:
        job.status = "failed"
        job.message = str(e)

    return job


def get_job(job_id: str):
    return JOBS.get(job_id)
