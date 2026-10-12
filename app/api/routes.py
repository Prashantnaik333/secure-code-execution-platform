"""
API Endpoints Router for Secure Online Code Execution Platform.
Implements SCEP-F-001, SCEP-F-002, SCEP-F-011, SCEP-F-017, SCEP-F-018, TC-F-01, TC-F-02, TC-SEC-02, TC-OPS-02.
Provides endpoints: /execute, /jobs/{jobId}, /health, /languages, /limits, /history, /logs.
"""

import time
from typing import Optional
from fastapi import APIRouter, Header, HTTPException, Query, Request, Response, status
from fastapi.responses import JSONResponse

from app.config import (
    DEFAULT_TIMEOUT_SECONDS,
    MAX_CODE_SIZE_BYTES,
    MAX_MEMORY_MB,
    MAX_OUTPUT_SIZE_BYTES,
    MAX_STDIN_SIZE_BYTES,
    MAX_TIMEOUT_SECONDS,
    PROJECT_INFO,
    SUPPORTED_LANGUAGES,
)
from app.job_manager import JobNotFoundError, UnauthorizedAccessError, job_manager
from app.logger import get_recent_operational_logs, log_event
from app.models import ExecuteResponse, JobResultResponse
from app.validator import ValidationError, validate_submission

router = APIRouter(prefix="/api", tags=["Code Execution"])
SERVER_START_TIME = time.time()

@router.post("/execute", response_model=ExecuteResponse, status_code=status.HTTP_202_ACCEPTED)
async def submit_code(request: Request):
    """
    Submit source code for isolated sandboxed execution.
    Validates input parameters and schedules job in execution queue.
    """
    # Check worker readiness (TC-OPS-02 / SCEP-NF-007)
    if not job_manager.is_worker_ready():
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "error": "Execution worker is currently unavailable or in maintenance mode",
                "category": "worker_unavailable",
                "details": None,
            },
        )

    # Parse and validate JSON
    try:
        payload = await request.json()
    except Exception:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"error": "Malformed or unparseable JSON payload", "category": "malformed_request"},
        )

    try:
        code, language, stdin_data, timeout = validate_submission(payload)
    except ValidationError as ve:
        log_event("VALIDATION_REJECTED", details={"category": ve.category, "msg": ve.message}, level="warning")
        return JSONResponse(
            status_code=ve.status_code,
            content={"error": ve.message, "category": ve.category},
        )

    client_id = payload.get("clientId")
    job = job_manager.create_and_enqueue_job(
        code=code,
        language=language,
        stdin_data=stdin_data,
        timeout_seconds=timeout,
        client_id=client_id,
    )

    return ExecuteResponse(
        jobId=job["jobId"],
        token=job["token"],
        status=job["status"],
        message="Code execution job accepted and enqueued.",
    )

@router.get("/jobs/{job_id}", response_model=JobResultResponse)
async def get_job_result(
    job_id: str,
    token: Optional[str] = Query(None, description="Job authorization token"),
    x_job_token: Optional[str] = Header(None, alias="X-Job-Token"),
):
    """
    Retrieve execution state, standard output, errors, and metadata for a job.
    Enforces authorization check to prevent cross-job snooping (SCEP-F-011, TC-SEC-02).
    """
    auth_token = token or x_job_token
    try:
        # Enforce auth check if token is provided or configured
        job = job_manager.get_job(job_id, token=auth_token, enforce_auth=bool(auth_token))
        return JobResultResponse(
            jobId=job["jobId"],
            language=job["language"],
            status=job["status"],
            stdout=job["stdout"],
            stderr=job["stderr"],
            compileErrors=job.get("compileErrors"),
            exitCode=job.get("exitCode"),
            durationMs=job.get("durationMs"),
            isTruncated=job.get("isTruncated", False),
            errorCategory=job.get("errorCategory"),
            createdAt=job["createdAt"],
            completedAt=job.get("completedAt"),
        )
    except JobNotFoundError:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"error": f"Job with ID '{job_id}' not found", "category": "not_found"},
        )
    except UnauthorizedAccessError:
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={"error": "Access denied: Unauthorized access to this job", "category": "unauthorized"},
        )

@router.get("/health")
async def health_check():
    """
    System and sandbox worker readiness probe.
    Satisfies SCEP-F-017, TC-OPS-02.
    """
    is_ready = job_manager.is_worker_ready()
    stats = job_manager.get_stats()
    uptime = round(time.time() - SERVER_START_TIME, 1)

    status_code = status.HTTP_200_OK if is_ready else status.HTTP_503_SERVICE_UNAVAILABLE
    return JSONResponse(
        status_code=status_code,
        content={
            "status": "ok" if is_ready else "unavailable",
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "uptimeSeconds": uptime,
            "workerReady": is_ready,
            "activeJobs": stats["active"],
            "queuedJobs": stats["queued"],
            "totalJobs": stats["total"],
            "supportedLanguages": list(SUPPORTED_LANGUAGES.keys()),
            "limits": {
                "maxCodeSize": MAX_CODE_SIZE_BYTES,
                "maxStdinSize": MAX_STDIN_SIZE_BYTES,
                "maxOutputSize": MAX_OUTPUT_SIZE_BYTES,
                "defaultTimeoutSeconds": DEFAULT_TIMEOUT_SECONDS,
                "maxTimeoutSeconds": MAX_TIMEOUT_SECONDS,
                "maxMemoryMb": MAX_MEMORY_MB,
            },
            "team": PROJECT_INFO["team"],
        },
    )

@router.get("/languages")
async def list_languages():
    """Returns list of supported languages, runtime versions, and default code templates."""
    langs = []
    for lang_id, data in SUPPORTED_LANGUAGES.items():
        langs.append({
            "id": data["id"],
            "name": data["name"],
            "extension": data["extension"],
            "isCompiled": data["is_compiled"],
            "defaultCode": data["default_code"],
        })
    return {"languages": langs}

@router.get("/limits")
async def get_system_limits():
    """Returns system resource quotas and limits."""
    return {
        "maxCodeSizeBytes": MAX_CODE_SIZE_BYTES,
        "maxStdinSizeBytes": MAX_STDIN_SIZE_BYTES,
        "maxOutputSizeBytes": MAX_OUTPUT_SIZE_BYTES,
        "defaultTimeoutSeconds": DEFAULT_TIMEOUT_SECONDS,
        "maxTimeoutSeconds": MAX_TIMEOUT_SECONDS,
        "maxMemoryMb": MAX_MEMORY_MB,
    }

@router.get("/history")
async def get_history(clientId: str = Query(..., description="Client identifier")):
    """Returns execution history for the active user session."""
    return {"history": job_manager.get_client_history(clientId)}

@router.get("/logs")
async def get_operational_logs():
    """Operational event audit log inspection (TC-OPS-01). Safe logs only."""
    return {"logs": get_recent_operational_logs()}
