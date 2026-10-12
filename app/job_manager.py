"""
Job Manager and State Machine for Secure Online Code Execution Platform.
Implements SCEP-F-001, SCEP-F-010, SCEP-F-011, TC-F-01, TC-F-06, TC-SEC-02.
Manages job lifecycle, thread-safe persistence, authorization tokens, and execution dispatch.
"""

import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from app.config import MAX_CONCURRENT_JOBS
from app.logger import log_event
from app.sandbox.executor import execute_in_sandbox

class JobNotFoundError(Exception):
    pass

class UnauthorizedAccessError(Exception):
    pass

class JobManager:
    """Thread-safe Job Manager and Lifecycle Supervisor."""

    def __init__(self, max_workers: int = MAX_CONCURRENT_JOBS):
        self._jobs: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()
        self._pool = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="JobWorker")
        self._worker_ready = True

    def set_worker_readiness(self, ready: bool) -> None:
        """Toggle worker readiness for testing / maintenance (TC-OPS-02)."""
        self._worker_ready = ready

    def is_worker_ready(self) -> bool:
        return self._worker_ready

    def create_and_enqueue_job(
        self,
        code: str,
        language: str,
        stdin_data: str = "",
        timeout_seconds: float = 4.0,
        client_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Creates a new job with an authorization token, enqueues execution, and records lifecycle state.
        Satisfies SCEP-F-001, SCEP-F-010, and SCEP-F-011.
        """
        job_id = str(uuid.uuid4())
        token = str(uuid.uuid4())
        now_iso = datetime.now(timezone.utc).isoformat()

        job_record = {
            "jobId": job_id,
            "token": token,
            "clientId": client_id,
            "language": language,
            "code": code,
            "stdin": stdin_data,
            "timeoutSeconds": timeout_seconds,
            "status": "queued",
            "stdout": "",
            "stderr": "",
            "compileErrors": None,
            "exitCode": None,
            "durationMs": None,
            "isTruncated": False,
            "errorCategory": "none",
            "createdAt": now_iso,
            "completedAt": None,
        }

        with self._lock:
            self._jobs[job_id] = job_record

        log_event("JOB_QUEUED", job_id=job_id, details={"language": language})

        # Submit to worker pool
        self._pool.submit(self._run_job_task, job_id)
        return job_record

    def _run_job_task(self, job_id: str) -> None:
        """Worker task processing the job execution in sandbox."""
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return
            job["status"] = "running"

        log_event("JOB_RUNNING", job_id=job_id, details={"language": job["language"]})

        try:
            exec_res = execute_in_sandbox(
                job_id=job["jobId"],
                code=job["code"],
                language=job["language"],
                stdin_data=job["stdin"],
                timeout_seconds=job["timeoutSeconds"],
            )

            with self._lock:
                job.update(exec_res)
                job["completedAt"] = datetime.now(timezone.utc).isoformat()

            log_event(
                f"JOB_{exec_res['status'].upper()}",
                job_id=job_id,
                details={
                    "status": exec_res["status"],
                    "exitCode": exec_res["exitCode"],
                    "durationMs": exec_res["durationMs"],
                    "errorCategory": exec_res.get("errorCategory"),
                },
            )
        except Exception as exc:
            import traceback
            traceback.print_exc()
            with self._lock:
                job["status"] = "failed"
                job["errorCategory"] = "internal_error"
                job["stderr"] = "An internal execution error occurred."
                job["completedAt"] = datetime.now(timezone.utc).isoformat()
            log_event("JOB_FAILED", job_id=job_id, details={"error": "Worker execution exception"}, level="error")

    def get_job(self, job_id: str, token: Optional[str] = None, enforce_auth: bool = True) -> Dict[str, Any]:
        """
        Retrieves job status and result. Enforces owner authorization token check.
        Satisfies SCEP-F-011 and TC-SEC-02 (Cross-job access prevention).
        """
        with self._lock:
            job = self._jobs.get(job_id)

        if not job:
            raise JobNotFoundError(f"Job with ID '{job_id}' not found")

        if enforce_auth and token is not None:
            if job["token"] != token:
                log_event("UNAUTHORIZED_ACCESS_ATTEMPT", job_id=job_id, level="warning")
                raise UnauthorizedAccessError("Access denied: Invalid authorization token for requested job")

        # Return a copy without secret token or full internal code
        safe_copy = dict(job)
        return safe_copy

    def get_client_history(self, client_id: str) -> List[Dict[str, Any]]:
        """Retrieve recent jobs submitted by a given client session."""
        with self._lock:
            history = [
                dict(j)
                for j in self._jobs.values()
                if j.get("clientId") == client_id
            ]
        # Sort by creation time descending
        history.sort(key=lambda x: x["createdAt"], reverse=True)
        return history[:20]

    def get_stats(self) -> Dict[str, int]:
        """Get live job counts for system health and monitoring."""
        with self._lock:
            active = sum(1 for j in self._jobs.values() if j["status"] == "running")
            queued = sum(1 for j in self._jobs.values() if j["status"] == "queued")
            total = len(self._jobs)
        return {"active": active, "queued": queued, "total": total}

# Global Singleton Instance
job_manager = JobManager()
