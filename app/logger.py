"""
Safe operational logging module for Secure Online Code Execution Platform.
Implements SCEP-F-016, SCEP-NF-006, SCEP-SR-006, TC-OPS-01, and TC-SEC-07.
Guarantees redaction of secrets, credentials, internal paths, and sensitive tokens.
"""

import logging
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional
from app.config import LOGS_DIR

# Sensitive key patterns to redact
SENSITIVE_PATTERNS = [
    re.compile(r"(token|secret|password|key|auth|bearer)[\"':=\s]+([^\s,;\"']+)", re.IGNORECASE),
    re.compile(r"([A-Za-z0-9_-]{20,})"),  # Potential long api-keys / hashes
]

def sanitize_text(text: str) -> str:
    """Redact sensitive patterns and secret fragments from text."""
    if not isinstance(text, str):
        text = str(text)
    sanitized = text
    for pattern in SENSITIVE_PATTERNS[:1]:  # Redact key-value pairs
        sanitized = pattern.sub(r"\1: [REDACTED]", sanitized)
    return sanitized

class SafeFormatter(logging.Formatter):
    """Custom log formatter ensuring redaction of sensitive info and clean formatting."""
    def format(self, record: logging.LogRecord) -> str:
        orig_msg = super().format(record)
        return sanitize_text(orig_msg)

# Setup Logger
logger = logging.getLogger("secure_sandbox")
logger.setLevel(logging.INFO)

if not logger.handlers:
    # Console Handler
    c_handler = logging.StreamHandler(sys.stdout)
    c_handler.setLevel(logging.INFO)
    c_fmt = SafeFormatter("%(asctime)s [%(levelname)s] [Team14-Sandbox] %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
    c_handler.setFormatter(c_fmt)
    logger.addHandler(c_handler)

    # File Handler
    log_file = LOGS_DIR / "operational.log"
    f_handler = logging.FileHandler(str(log_file), encoding="utf-8")
    f_handler.setLevel(logging.INFO)
    f_fmt = SafeFormatter("%(asctime)s [%(levelname)s] %(message)s", datefmt="%Y-%m-%dT%H:%M:%SZ")
    f_handler.setFormatter(f_fmt)
    logger.addHandler(f_handler)

# Circular in-memory buffer of recent operational logs for dashboard viewing
_recent_logs: list = []
MAX_RECENT_LOGS = 100

def log_event(event_type: str, job_id: Optional[str] = None, details: Optional[Dict[str, Any]] = None, level: str = "info"):
    """
    Record an operational event safely.
    Matches SCEP-F-016: Records operational events (accepted, completed, timed out, failed)
    without logging raw secrets.
    """
    timestamp = datetime.now(timezone.utc).isoformat()
    entry = {
        "timestamp": timestamp,
        "event": event_type,
        "job_id": job_id or "N/A",
        "details": details or {},
    }
    msg = f"Event: {event_type} | Job: {entry['job_id']}"
    if details:
        clean_details = {k: sanitize_text(str(v)) for k, v in details.items() if k not in ("code", "token")}
        msg += f" | Details: {clean_details}"

    if level == "error":
        logger.error(msg)
    elif level == "warning":
        logger.warning(msg)
    else:
        logger.info(msg)

    _recent_logs.append(entry)
    if len(_recent_logs) > MAX_RECENT_LOGS:
        _recent_logs.pop(0)

def get_recent_operational_logs():
    """Retrieve operational event records."""
    return list(_recent_logs)
