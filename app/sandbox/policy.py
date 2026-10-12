"""
Security Policy and Isolation Engine for Secure Online Code Execution Platform.
Implements SCEP-F-004, SCEP-F-013, SCEP-F-014, TC-SEC-01, TC-SEC-04, TC-SEC-05.
Provides environment sanitization, sandbox hooks generation, and security checks.
"""

import json
import os
import sys
from pathlib import Path
from typing import Dict
from app.config import SAFE_ENV_KEYS

def get_sanitized_environment(job_workspace: Path) -> Dict[str, str]:
    """
    Constructs a minimal, least-privilege environment for sandboxed processes.
    Strips all host secrets, user tokens, SSH keys, credentials, and app env vars.
    Satisfies TC-SEC-01 (Least privilege sandbox / no host secrets exposed).
    """
    clean_env: Dict[str, str] = {}
    for key, val in os.environ.items():
        if key.upper() in SAFE_ENV_KEYS:
            clean_env[key] = val

    # Override temporary directory pointers to point strictly inside the job workspace
    clean_env["TEMP"] = str(job_workspace)
    clean_env["TMP"] = str(job_workspace)
    clean_env["TMPDIR"] = str(job_workspace)

    # Force Python to use workspace for sitecustomize and disable stdout buffering
    clean_env["PYTHONUNBUFFERED"] = "1"
    clean_env["PYTHONIOENCODING"] = "utf-8"
    clean_env["PYTHONUTF8"] = "1"
    clean_env["PYTHONPATH"] = str(job_workspace)

    # Block common network proxies or remote endpoints
    clean_env["HTTP_PROXY"] = "http://127.0.0.1:0"
    clean_env["HTTPS_PROXY"] = "http://127.0.0.1:0"
    clean_env["ALL_PROXY"] = "http://127.0.0.1:0"
    clean_env["NO_PROXY"] = ""

    return clean_env

def inject_sandbox_guards(job_workspace: Path, language: str) -> None:
    """
    Injects runtime security guards into the job workspace.
    Enforces SCEP-F-013 (Filesystem Isolation / TC-SEC-04)
    and SCEP-F-014 (Network Restriction / TC-SEC-05).
    """
    if language == "python":
        hook_path = job_workspace / "sitecustomize.py"
        py_prefix = str(Path(sys.prefix).resolve()).replace("\\", "\\\\")
        ws_str = str(job_workspace.resolve()).replace("\\", "\\\\")
        hook_content = f"""# Sandbox Isolation Guard (SCEP-F-013, SCEP-F-014)
import builtins
import os
import pathlib
import socket

_orig_open = builtins.open
_workspace = pathlib.Path(r"{ws_str}").resolve()
_allowed_prefix = pathlib.Path(r"{py_prefix}").resolve()

def _safe_open(file, *args, **kwargs):
    if isinstance(file, (str, bytes, os.PathLike)):
        try:
            resolved = pathlib.Path(file).resolve()
            res_str = str(resolved).lower()
            ws_str = str(_workspace).lower()
            pfx_str = str(_allowed_prefix).lower()
            if not (res_str.startswith(ws_str) or res_str.startswith(pfx_str)):
                raise PermissionError(f"Sandbox violation: Access to '{{file}}' outside the sandbox workspace is prohibited (SCEP-F-013, TC-SEC-04)")
        except Exception:
            raise
    return _orig_open(file, *args, **kwargs)

builtins.open = _safe_open

# Disable outbound network connections (SCEP-F-014, TC-SEC-05)
_orig_connect = socket.socket.connect
def _safe_connect(self, address):
    raise PermissionError("Sandbox violation: Outbound network connections are blocked by default security policy (SCEP-F-014, TC-SEC-05)")
socket.socket.connect = _safe_connect
"""
        hook_path.write_text(hook_content, encoding="utf-8")

    elif language == "javascript":
        hook_path = job_workspace / "_preload_guard.js"
        ws_json = json.dumps(str(job_workspace.resolve()))
        hook_content = f"""// Node.js Sandbox Isolation Guard (SCEP-F-013, SCEP-F-014)
const fs = require('fs');
const path = require('path');
const net = require('net');
const ws = path.resolve({ws_json});

function verifyPath(target) {{
    if (typeof target === 'string') {{
        const resolved = path.resolve(target);
        if (!resolved.toLowerCase().startsWith(ws.toLowerCase())) {{
            throw new Error(`Sandbox violation: Access to '${{target}}' is prohibited outside workspace (SCEP-F-013, TC-SEC-04)`);
        }}
    }}
}}

const origReadFileSync = fs.readFileSync;
fs.readFileSync = function(file, options) {{
    verifyPath(file);
    return origReadFileSync.apply(this, arguments);
}};

const origReadFile = fs.readFile;
fs.readFile = function(file, options, callback) {{
    verifyPath(file);
    return origReadFile.apply(this, arguments);
}};

// Block network connects
const origNetConnect = net.Socket.prototype.connect;
net.Socket.prototype.connect = function() {{
    throw new Error('Sandbox violation: Outbound network sockets are blocked by security policy (SCEP-F-014, TC-SEC-05)');
}};
"""
        hook_path.write_text(hook_content, encoding="utf-8")
