"""
Security and Sandbox Boundary Tests for Secure Online Code Execution Platform.
Implements test cases TC-SEC-01 to TC-SEC-07 from Software Test Plan (STP).
Traceable to SRS requirements SCEP-F-004, 011, 012, 013, 014, 015, SCEP-SR-001..006.
"""

import os
import time
import pytest
from app.config import MAX_CODE_SIZE_BYTES, MAX_STDIN_SIZE_BYTES, SANDBOX_BASE_DIR

def wait_for_job(client, job_id, token, max_wait=10.0):
    start = time.time()
    while time.time() - start < max_wait:
        res = client.get(f"/api/jobs/{job_id}?token={token}")
        assert res.status_code == 200
        data = res.json()
        if data["status"] not in ("queued", "running"):
            return data
        time.sleep(0.1)
    raise TimeoutError(f"Job {job_id} did not complete within {max_wait}s")

class TestSecurity:

    def test_tc_sec_01_sandbox_environment_least_privilege(self, client):
        """TC-SEC-01: Sandboxed process has clean environment; no host secrets or custom tokens."""
        os.environ["SECRET_TOKEN_HOST"] = "super_secret_host_key_12345"

        probe_code = (
            "import os\n"
            "found = 'SECRET_TOKEN_HOST' in os.environ\n"
            "print(f'SECRET_FOUND={found}')\n"
        )
        res = client.post("/api/execute", json={"code": probe_code, "language": "python"})
        assert res.status_code == 202
        body = res.json()

        job_result = wait_for_job(client, body["jobId"], body["token"])
        assert job_result["status"] == "completed"
        assert "SECRET_FOUND=False" in job_result["stdout"]

    def test_tc_sec_02_cross_job_access_denied(self, client):
        """TC-SEC-02: Requesting job with invalid token is rejected with 403 Forbidden."""
        res = client.post("/api/execute", json={"code": "print('Private Job')", "language": "python"})
        assert res.status_code == 202
        body = res.json()
        job_id = body["jobId"]
        token = body["token"]

        # 1. Retrieve with correct token succeeds
        res_ok = client.get(f"/api/jobs/{job_id}?token={token}")
        assert res_ok.status_code == 200

        # 2. Retrieve with invalid/spoofed token fails safely (403 Forbidden)
        res_bad = client.get(f"/api/jobs/{job_id}?token=spoofed-invalid-token")
        assert res_bad.status_code == 403
        assert res_bad.json()["category"] == "unauthorized"

    def test_tc_sec_03_oversized_input_rejection(self, client):
        """TC-SEC-03: Oversized code (>64KB) or stdin (>16KB) rejected before worker invocation."""
        oversized_code = "# " + ("A" * (MAX_CODE_SIZE_BYTES + 500))
        res1 = client.post("/api/execute", json={"code": oversized_code, "language": "python"})
        assert res1.status_code == 413
        assert res1.json()["category"] == "payload_too_large"

        oversized_stdin = "B" * (MAX_STDIN_SIZE_BYTES + 500)
        res2 = client.post("/api/execute", json={
            "code": "print(1)",
            "language": "python",
            "stdin": oversized_stdin
        })
        assert res2.status_code == 413
        assert res2.json()["category"] == "payload_too_large"

    def test_tc_sec_04_filesystem_isolation(self, client):
        """TC-SEC-04: Cannot access or modify host files outside designated temporary sandbox."""
        probe_code = (
            "import os\n"
            "try:\n"
            "    with open('../../Team14_Secure_Code_Execution_SRS.docx', 'rb') as f:\n"
            "        print('HOST_FILE_ACCESSIBLE')\n"
            "except Exception as e:\n"
            "    print(f'PASS_BLOCKED_{type(e).__name__}')\n"
        )
        res = client.post("/api/execute", json={"code": probe_code, "language": "python"})
        assert res.status_code == 202
        body = res.json()

        job_result = wait_for_job(client, body["jobId"], body["token"])
        assert job_result["status"] == "completed"
        assert "HOST_FILE_ACCESSIBLE" not in job_result["stdout"]
        assert "PASS_BLOCKED" in job_result["stdout"]

    def test_tc_sec_05_network_restriction(self, client):
        """TC-SEC-05: Sandbox policy blocks outbound network sockets by default."""
        net_code = (
            "import socket\n"
            "try:\n"
            "    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)\n"
            "    s.settimeout(1.0)\n"
            "    s.connect(('8.8.8.8', 53))\n"
            "    print('FAIL_NETWORK_CONNECTED')\n"
            "except Exception as e:\n"
            "    print(f'PASS_NETWORK_BLOCKED_{type(e).__name__}')\n"
        )
        res = client.post("/api/execute", json={"code": net_code, "language": "python"})
        assert res.status_code == 202
        body = res.json()

        job_result = wait_for_job(client, body["jobId"], body["token"])
        assert job_result["status"] == "completed"
        assert "FAIL_NETWORK_CONNECTED" not in job_result["stdout"]
        assert "PASS_NETWORK_BLOCKED" in job_result["stdout"]

    def test_tc_sec_06_guaranteed_cleanup(self, client):
        """TC-SEC-06: Sandbox workspace directory is cleaned up after execution."""
        res = client.post("/api/execute", json={"code": "print('Cleanup test')", "language": "python"})
        body = res.json()
        job_id = body["jobId"]

        wait_for_job(client, job_id, body["token"])

        # Check that job workspace is removed
        job_dir = SANDBOX_BASE_DIR / f"job_{job_id}"
        assert not job_dir.exists()

    def test_tc_sec_07_safe_errors_no_stack_traces(self, client):
        """TC-SEC-07: Internal errors and bad payloads return safe messages without stack traces."""
        res = client.get("/api/jobs/00000000-0000-0000-0000-000000000000")
        assert res.status_code == 404
        data = res.json()
        assert "Traceback" not in data.get("error", "")
        assert data.get("category") == "not_found"
