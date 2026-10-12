"""
Sandbox Execution Engine for Secure Online Code Execution Platform.
Implements SCEP-F-003..009, SCEP-F-013..015, TC-F-03..05, TC-LIM-01..03, TC-SEC-04..06.
Handles compilation, bounded resource execution, timeout enforcement, output streaming, and cleanup.
Supports cross-platform execution (WSL Linux sandbox for C/C++, native JVM for Java, isolated Python & Node).
"""

import os
import shutil
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Any, Dict, Optional, Tuple
import psutil

from app.config import (
    DEFAULT_TIMEOUT_SECONDS,
    MAX_MEMORY_MB,
    MAX_OUTPUT_SIZE_BYTES,
    SANDBOX_BASE_DIR,
    SUPPORTED_LANGUAGES,
)
from app.sandbox.policy import get_sanitized_environment, inject_sandbox_guards

def is_wsl_available() -> bool:
    """Check if WSL Linux is available on Windows."""
    if os.name != "nt":
        return False
    try:
        r = subprocess.run(["wsl", "uname"], capture_output=True, timeout=3.0)
        return r.returncode == 0
    except Exception:
        return False

HAS_WSL = is_wsl_available()

def to_wsl_path(path: Path) -> str:
    """Convert Windows path to WSL /mnt path."""
    p_str = str(path.resolve()).replace("\\", "/")
    if len(p_str) > 1 and p_str[1] == ":":
        drive = p_str[0].lower()
        return f"/mnt/{drive}{p_str[2:]}"
    return p_str

def kill_process_tree(pid: int) -> None:
    """Recursively terminate a process and all its spawned child processes."""
    try:
        parent = psutil.Process(pid)
        children = parent.children(recursive=True)
        for child in children:
            try:
                child.kill()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        parent.kill()
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        pass

def cleanup_workspace(workspace: Path) -> None:
    """Ensure workspace directory and all temporary files are completely removed (TC-SEC-06)."""
    if workspace.exists():
        for _ in range(5):
            try:
                shutil.rmtree(workspace, ignore_errors=False)
                break
            except Exception:
                time.sleep(0.1)

def compile_code(lang_info: Dict[str, Any], workspace: Path, source_file: Path) -> Tuple[bool, str, Optional[Path]]:
    """
    Compiles code for compiled languages (C, C++, Java).
    Satisfies SCEP-F-003 and TC-F-03.
    """
    if not lang_info.get("is_compiled", False):
        return True, "", source_file

    lang_id = lang_info["id"]
    binary_path: Optional[Path] = None

    if lang_id in ("c", "cpp"):
        compiler = "gcc" if lang_id == "c" else "g++"
        if HAS_WSL:
            wsl_ws = to_wsl_path(workspace)
            binary_name = "program"
            binary_path = workspace / binary_name
            cmd = ["wsl", "bash", "-c", f"cd '{wsl_ws}' && {compiler} -O2 -Wall {source_file.name} -o {binary_name}"]
        else:
            binary_name = "program.exe" if os.name == "nt" else "program"
            binary_path = workspace / binary_name
            cmd = [compiler, "-O2", "-Wall", str(source_file.name), "-o", binary_name]
    elif lang_id == "java":
        cmd = ["javac", str(source_file.name)]
        binary_path = workspace / "Main.class"
    else:
        return False, f"Unknown compiled language: {lang_id}", None

    clean_env = get_sanitized_environment(workspace)
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(workspace),
            env=clean_env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=10.0,
        )
        diagnostics = (proc.stdout or "") + (proc.stderr or "")
        if proc.returncode != 0:
            return False, diagnostics.strip(), None
        return True, "", binary_path
    except subprocess.TimeoutExpired:
        return False, "Compilation timed out after 10.0 seconds", None
    except Exception as exc:
        return False, f"Compiler error: {str(exc)}", None

def execute_in_sandbox(
    job_id: str,
    code: str,
    language: str,
    stdin_data: str = "",
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
) -> Dict[str, Any]:
    """
    Executes user code in an isolated workspace with strict resource and output constraints.
    Returns structured execution result dictionary.
    """
    lang_info = SUPPORTED_LANGUAGES[language]
    workspace = SANDBOX_BASE_DIR / f"job_{job_id}"
    workspace.mkdir(parents=True, exist_ok=True)

    # Determine source file name
    if language == "java":
        source_file = workspace / "Main.java"
    else:
        ext = lang_info["extension"]
        source_file = workspace / f"main{ext}"

    # Write source code to workspace
    source_file.write_text(code, encoding="utf-8")

    # Inject runtime security guards (Filesystem / Network isolation)
    inject_sandbox_guards(workspace, language)

    # Result structure
    result: Dict[str, Any] = {
        "status": "running",
        "stdout": "",
        "stderr": "",
        "compileErrors": None,
        "exitCode": None,
        "durationMs": 0.0,
        "isTruncated": False,
        "errorCategory": "none",
    }

    start_time = time.time()
    proc: Optional[subprocess.Popen] = None

    try:
        # Step 1: Compilation if necessary (SCEP-F-003, TC-F-03)
        if lang_info.get("is_compiled", False):
            comp_ok, comp_diag, bin_path = compile_code(lang_info, workspace, source_file)
            if not comp_ok:
                result["status"] = "failed"
                result["compileErrors"] = comp_diag
                result["errorCategory"] = "compilation"
                result["exitCode"] = 1
                result["durationMs"] = round((time.time() - start_time) * 1000, 2)
                return result

        # Step 2: Prepare Execution Command
        clean_env = get_sanitized_environment(workspace)
        if language == "python":
            cmd = [sys.executable, str(source_file.name)]
        elif language == "javascript":
            cmd = ["node", "-r", "./_preload_guard.js", str(source_file.name)]
        elif language in ("c", "cpp"):
            if HAS_WSL:
                wsl_ws = to_wsl_path(workspace)
                cmd = ["wsl", "bash", "-c", f"cd '{wsl_ws}' && ./program"]
            else:
                binary_name = "program.exe" if os.name == "nt" else "program"
                cmd = [str(workspace / binary_name)]
        elif language == "java":
            cmd = ["java", "-cp", ".", "Main"]
        else:
            result["status"] = "rejected"
            result["errorCategory"] = "unsupported_language"
            return result

        # Step 3: Launch Process
        run_start = time.time()
        proc = subprocess.Popen(
            cmd,
            cwd=str(workspace),
            env=clean_env,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=False,
        )

        # Write stdin if provided
        if stdin_data and proc.stdin:
            try:
                proc.stdin.write(stdin_data.encode("utf-8"))
                proc.stdin.flush()
                proc.stdin.close()
            except Exception:
                pass
        elif proc.stdin:
            try:
                proc.stdin.close()
            except Exception:
                pass

        # Buffers and streaming controls
        stdout_bytes = bytearray()
        stderr_bytes = bytearray()
        is_truncated = [False]
        output_flooded = [False]
        max_bytes = MAX_OUTPUT_SIZE_BYTES
        max_mem_bytes = MAX_MEMORY_MB * 1024 * 1024
        stop_threads = threading.Event()

        def stream_reader(pipe, buf, is_stdout=True):
            try:
                while not stop_threads.is_set():
                    chunk = pipe.read(4096)
                    if not chunk:
                        break
                    if len(buf) + len(chunk) > max_bytes:
                        remaining = max(0, max_bytes - len(buf))
                        if remaining > 0:
                            buf.extend(chunk[:remaining])
                        is_truncated[0] = True
                        output_flooded[0] = True
                        if proc and proc.pid:
                            kill_process_tree(proc.pid)
                        break
                    else:
                        buf.extend(chunk)
            except Exception:
                pass
            finally:
                try:
                    pipe.close()
                except Exception:
                    pass

        out_thread = threading.Thread(target=stream_reader, args=(proc.stdout, stdout_bytes, True), daemon=True)
        err_thread = threading.Thread(target=stream_reader, args=(proc.stderr, stderr_bytes, False), daemon=True)
        out_thread.start()
        err_thread.start()

        # Step 4: Monitor Execution with Limit Enforcement
        poll_interval = 0.05
        timed_out = False
        memory_exceeded = False

        while True:
            elapsed = time.time() - run_start

            # Enforce Wall-Clock Timeout (SCEP-F-005, TC-LIM-01)
            if elapsed > timeout_seconds:
                timed_out = True
                kill_process_tree(proc.pid)
                break

            # Enforce Memory Limit (SCEP-F-006, TC-LIM-02)
            try:
                p = psutil.Process(proc.pid)
                total_mem = p.memory_info().rss
                for child in p.children(recursive=True):
                    try:
                        total_mem += child.memory_info().rss
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        pass
                if total_mem > max_mem_bytes:
                    memory_exceeded = True
                    kill_process_tree(proc.pid)
                    break
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass

            # Check if process exited or output flooded
            if output_flooded[0]:
                break

            ret = proc.poll()
            if ret is not None:
                break

            time.sleep(poll_interval)

        # Signal reader threads to finish
        stop_threads.set()
        out_thread.join(timeout=0.5)
        err_thread.join(timeout=0.5)

        # Compute Duration (TC-F-05)
        duration_ms = round((time.time() - run_start) * 1000, 2)
        result["durationMs"] = duration_ms
        result["isTruncated"] = is_truncated[0]

        # Decode output safely
        stdout_str = stdout_bytes.decode("utf-8", errors="replace")
        stderr_str = stderr_bytes.decode("utf-8", errors="replace")

        if is_truncated[0]:
            stdout_str += "\n[OUTPUT TRUNCATED: Exceeded 64KB output limit]"

        result["stdout"] = stdout_str
        result["stderr"] = stderr_str

        # Assign Status and Error Categories
        if timed_out:
            result["status"] = "timed_out"
            result["errorCategory"] = "timeout"
            result["exitCode"] = -1
            result["stderr"] += (
                f"\nExecution timed out: Maximum time limit ({timeout_seconds:.1f}s) exceeded."
            )
        elif memory_exceeded:
            result["status"] = "failed"
            result["errorCategory"] = "resource_limit"
            result["exitCode"] = -2
            result["stderr"] += (
                f"\nResource limit exceeded: Process exceeded maximum memory limit ({MAX_MEMORY_MB} MB)."
            )
        elif output_flooded[0]:
            result["status"] = "completed"
            result["errorCategory"] = "none"
            result["exitCode"] = 0
        else:
            exit_code = proc.returncode if proc.returncode is not None else 0
            result["exitCode"] = exit_code
            if exit_code == 0:
                result["status"] = "completed"
                result["errorCategory"] = "none"
            else:
                result["status"] = "failed"
                result["errorCategory"] = "runtime"

        return result

    finally:
        # Step 6: Guaranteed Cleanup (SCEP-F-015, TC-SEC-06)
        if proc and proc.pid:
            kill_process_tree(proc.pid)
        cleanup_workspace(workspace)
