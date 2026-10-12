"""
Data models and schemas for Secure Online Code Execution Platform.
Defines input payloads, result shapes, and structured error responses.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

class ExecuteRequest(BaseModel):
    code: str = Field(..., description="Source code to execute")
    language: str = Field(..., description="Target language identifier (e.g. python, javascript, c, cpp, java)")
    stdin: Optional[str] = Field(default="", description="Optional standard input stream")
    timeoutSeconds: Optional[float] = Field(default=None, description="Optional custom timeout up to MAX_TIMEOUT")
    clientId: Optional[str] = Field(default=None, description="Client session identifier")

class ExecuteResponse(BaseModel):
    jobId: str
    token: str
    status: str
    message: str

class JobResultResponse(BaseModel):
    jobId: str
    language: str
    status: str
    stdout: str = ""
    stderr: str = ""
    compileErrors: Optional[str] = None
    exitCode: Optional[int] = None
    durationMs: Optional[float] = None
    isTruncated: bool = False
    errorCategory: Optional[str] = None
    createdAt: str
    completedAt: Optional[str] = None

class ErrorResponse(BaseModel):
    error: str
    category: str
    details: Optional[Dict[str, Any]] = None

class HealthResponse(BaseModel):
    status: str
    timestamp: str
    uptimeSeconds: float
    workerReady: bool
    activeJobs: int
    queuedJobs: int
    supportedLanguages: List[str]
    limits: Dict[str, Any]
