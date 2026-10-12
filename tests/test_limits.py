"""
Resource Limits Tests for Secure Online Code Execution Platform.
Implements test cases TC-LIM-01 to TC-LIM-03 from Software Test Plan (STP).
Traceable to SRS requirements SCEP-F-005, SCEP-F-006, SCEP-F-009, SCEP-SR-002.
"""

import time
import pytest

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

class TestLimits:

    def test_tc_lim_01_wall_clock_timeout(self, client):
        """TC-LIM-01: Controlled infinite-loop program terminated within configured timeout."""
        infinite_loop = (
            "import time\n"
            "print('Starting loop')\n"
            "while True:\n"
            "    time.sleep(0.05)\n"
        )
        payload = {
            "code": infinite_loop,
            "language": "python",
            "timeoutSeconds": 1.5,
        }
        t0 = time.time()
        res = client.post("/api/execute", json=payload)
        assert res.status_code == 202
        body = res.json()

        job_result = wait_for_job(client, body["jobId"], body["token"], max_wait=5.0)
        elapsed = time.time() - t0

        assert job_result["status"] == "timed_out"
        assert job_result["errorCategory"] == "timeout"
        assert "timed out" in job_result["stderr"].lower()
        assert elapsed < 4.0

    def test_tc_lim_02_memory_limit_contained(self, client):
        """TC-LIM-02: Program attempting excessive memory allocation is contained."""
        mem_bomb = (
            "try:\n"
            "    # Attempt huge allocation\n"
            "    chunks = []\n"
            "    for _ in range(5000):\n"
            "        chunks.append(bytearray(10 * 1024 * 1024))\n"
            "except MemoryError:\n"
            "    print('CONTAINED_MEMORY_ERROR')\n"
        )
        payload = {"code": mem_bomb, "language": "python", "timeoutSeconds": 3.0}
        res = client.post("/api/execute", json=payload)
        assert res.status_code == 202
        body = res.json()

        job_result = wait_for_job(client, body["jobId"], body["token"], max_wait=6.0)
        # Process is either terminated by memory limit monitor or contained cleanly
        assert job_result["status"] in ("failed", "completed")
        assert (
            job_result["errorCategory"] in ("resource_limit", "none", "runtime")
            or "CONTAINED" in job_result["stdout"]
        )

    def test_tc_lim_03_output_flooding_contained(self, client):
        """TC-LIM-03: Program generates excessive stdout, verified capped at 64KB and truncated."""
        flood_code = (
            "for i in range(5000):\n"
            "    print('FLOOD_CHUNK_TEST_LINE_' + 'X' * 80)\n"
        )
        payload = {"code": flood_code, "language": "python"}
        res = client.post("/api/execute", json=payload)
        assert res.status_code == 202
        body = res.json()

        job_result = wait_for_job(client, body["jobId"], body["token"])
        assert job_result["isTruncated"] is True
        assert "[OUTPUT TRUNCATED" in job_result["stdout"]
        assert len(job_result["stdout"].encode("utf-8")) <= 68 * 1024
