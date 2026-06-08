"""Connector job persistence under .decision_system/connectors/jobs/."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from decision_system.connectors.models import ConnectorImportJob

DEFAULT_JOBS_DIR = Path(".decision_system") / "connectors" / "jobs"


def _jobs_dir() -> Path:
    path = DEFAULT_JOBS_DIR
    path.mkdir(parents=True, exist_ok=True)
    return path


def _job_path(job_id: str) -> Path:
    return _jobs_dir() / f"{job_id}.json"


def save_job(job: ConnectorImportJob) -> Path:
    """Persist a ConnectorImportJob to disk. Returns the written path."""
    path = _job_path(job.job_id)
    payload = job.model_dump(mode="json")
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return path


def append_job(job: ConnectorImportJob) -> Path:
    """Persist a job. Alias for save_job for clarity."""
    return save_job(job)


def get_job(job_id: str) -> ConnectorImportJob | None:
    """Load a single job by id, or None if not found."""
    path = _job_path(job_id)
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    return ConnectorImportJob.model_validate(data)


def load_jobs() -> list[ConnectorImportJob]:
    """Load all persisted connector jobs, sorted newest-first by job_id."""
    jobs: list[ConnectorImportJob] = []
    for path in sorted(_jobs_dir().glob("*.json"), reverse=True):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            jobs.append(ConnectorImportJob.model_validate(data))
        except Exception:
            continue
    return jobs


def delete_job(job_id: str) -> bool:
    """Delete a persisted job by id. Returns True if it existed."""
    path = _job_path(job_id)
    if path.exists():
        path.unlink()
        return True
    return False


class ConnectorJobStore:
    """Thin object-oriented facade over the module-level store helpers."""

    def __init__(self, jobs_dir: Path | None = None) -> None:
        self._jobs_dir = jobs_dir or DEFAULT_JOBS_DIR
        self._jobs_dir.mkdir(parents=True, exist_ok=True)

    def save(self, job: ConnectorImportJob) -> Path:
        path = self._jobs_dir / f"{job.job_id}.json"
        payload = job.model_dump(mode="json")
        path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        return path

    def get(self, job_id: str) -> ConnectorImportJob | None:
        path = self._jobs_dir / f"{job_id}.json"
        if not path.exists():
            return None
        data = json.loads(path.read_text(encoding="utf-8"))
        return ConnectorImportJob.model_validate(data)

    def load_all(self) -> list[ConnectorImportJob]:
        jobs: list[ConnectorImportJob] = []
        try:
            items = sorted(self._jobs_dir.glob("*.json"), reverse=True)
        except Exception:
            return jobs
        for path in items:
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                jobs.append(ConnectorImportJob.model_validate(data))
            except Exception:
                continue
        return jobs

    def delete(self, job_id: str) -> bool:
        path = self._jobs_dir / f"{job_id}.json"
        if path.exists():
            path.unlink()
            return True
        return False
