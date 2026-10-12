"""
Input Validation Module for Secure Online Code Execution Platform.
Implements SCEP-F-002, SCEP-F-012, and TC-SEC-03.
Validates code presence, size limits, language allowlist, and stdin constraints.
"""

from typing import Dict, Optional, Tuple
from app.config import (
    MAX_CODE_SIZE_BYTES,
    MAX_STDIN_SIZE_BYTES,
    MAX_TIMEOUT_SECONDS,
    SUPPORTED_LANGUAGES,
)

class ValidationError(Exception):
    def __init__(self, message: str, status_code: int = 400, category: str = "validation"):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.category = category

def validate_submission(payload: Dict) -> Tuple[str, str, str, float]:
    """
    Validates submission payload before scheduling.
    Returns normalized (code, language, stdin, timeout_seconds).
    Raises ValidationError if invalid or oversized.
    """
    if not isinstance(payload, dict):
        raise ValidationError("Request payload must be a JSON object", status_code=400, category="malformed_request")

    # 1. Code Validation
    raw_code = payload.get("code")
    if raw_code is None:
        raise ValidationError("Field 'code' is required and cannot be null", status_code=400, category="missing_code")
    if not isinstance(raw_code, str) or not raw_code.strip():
        raise ValidationError("Submitted code cannot be empty or only whitespace", status_code=400, category="empty_code")

    code_bytes = len(raw_code.encode("utf-8"))
    if code_bytes > MAX_CODE_SIZE_BYTES:
        raise ValidationError(
            f"Code size ({code_bytes} bytes) exceeds maximum allowable limit of {MAX_CODE_SIZE_BYTES} bytes",
            status_code=413,
            category="payload_too_large"
        )

    # 2. Language Validation
    raw_lang = payload.get("language")
    if not raw_lang or not isinstance(raw_lang, str):
        raise ValidationError("Field 'language' is required and must be a non-empty string", status_code=400, category="invalid_language")

    norm_lang = raw_lang.strip().lower()
    if norm_lang not in SUPPORTED_LANGUAGES:
        valid_langs = ", ".join(SUPPORTED_LANGUAGES.keys())
        raise ValidationError(
            f"Unsupported language '{raw_lang}'. Supported languages are: {valid_langs}",
            status_code=400,
            category="unsupported_language"
        )

    # 3. Stdin Validation
    raw_stdin = payload.get("stdin", "")
    if raw_stdin is None:
        raw_stdin = ""
    elif not isinstance(raw_stdin, str):
        raise ValidationError("Field 'stdin' must be a string", status_code=400, category="invalid_stdin")

    stdin_bytes = len(raw_stdin.encode("utf-8"))
    if stdin_bytes > MAX_STDIN_SIZE_BYTES:
        raise ValidationError(
            f"Standard input size ({stdin_bytes} bytes) exceeds maximum allowable limit of {MAX_STDIN_SIZE_BYTES} bytes",
            status_code=413,
            category="payload_too_large"
        )

    # 4. Timeout Validation
    raw_timeout = payload.get("timeoutSeconds")
    timeout = 4.0
    if raw_timeout is not None:
        try:
            timeout = float(raw_timeout)
            if timeout <= 0.1 or timeout > MAX_TIMEOUT_SECONDS:
                raise ValidationError(
                    f"Timeout must be between 0.1 and {MAX_TIMEOUT_SECONDS} seconds",
                    status_code=400,
                    category="invalid_timeout"
                )
        except (ValueError, TypeError):
            raise ValidationError("Field 'timeoutSeconds' must be a valid positive number", status_code=400, category="invalid_timeout")

    return raw_code, norm_lang, raw_stdin, timeout
