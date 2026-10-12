"""
Operations and Non-Functional Tests for Secure Online Code Execution Platform.
Implements test cases TC-OPS-01, TC-OPS-02, TC-NF-01, TC-UX-01 from Software Test Plan (STP).
Traceable to SRS requirements SCEP-F-016, SCEP-F-017, SCEP-NF-001, SCEP-NF-004, SCEP-NF-007.
"""

import time
import pytest
from app.job_manager import job_manager

class TestOperations:

    def test_tc_ops_01_operational_logging(self, client):
        """TC-OPS-01: Operational lifecycle events are recorded with safe diagnostic details."""
        res = client.post("/api/execute", json={"code": "print('Ops test')", "language": "python"})
        assert res.status_code == 202

        log_res = client.get("/api/logs")
        assert log_res.status_code == 200
        logs = log_res.json()["logs"]
        assert len(logs) > 0
        events = [entry["event"] for entry in logs]
        assert "JOB_QUEUED" in events

    def test_tc_ops_02_worker_unavailable_handling(self, client):
        """TC-OPS-02: When worker is unavailable, health endpoint reports 503 and execution is safely rejected."""
        try:
            # Simulate worker downtime / maintenance mode
            job_manager.set_worker_readiness(False)

            # Health endpoint should report 503
            h_res = client.get("/api/health")
            assert h_res.status_code == 503
            assert h_res.json()["workerReady"] is False

            # Submission should fail safely with 503
            sub_res = client.post("/api/execute", json={"code": "print(1)", "language": "python"})
            assert sub_res.status_code == 503
            assert sub_res.json()["category"] == "worker_unavailable"
        finally:
            job_manager.set_worker_readiness(True)

    def test_tc_nf_01_submission_latency_performance(self, client):
        """TC-NF-01: API submission acknowledgement is returned within 2 seconds."""
        latencies = []
        for _ in range(5):
            t0 = time.time()
            res = client.post("/api/execute", json={"code": "x = 42", "language": "python"})
            lat = time.time() - t0
            assert res.status_code == 202
            latencies.append(lat)

        avg_lat = sum(latencies) / len(latencies)
        assert avg_lat < 2.0  # SCEP-NF-001 requirement: < 2.0s ack

    def test_tc_ux_01_error_result_clarity(self, client):
        """TC-UX-01: Clear and distinct categories for different errors."""
        res_syntax = client.post("/api/execute", json={"code": "def func(", "language": "python"})
        assert res_syntax.status_code == 202
        body = res_syntax.json()

        start = time.time()
        while time.time() - start < 5.0:
            job_res = client.get(f"/api/jobs/{body['jobId']}?token={body['token']}").json()
            if job_res["status"] not in ("queued", "running"):
                break
            time.sleep(0.1)

        assert job_res["status"] == "failed"
        assert job_res["errorCategory"] in ("runtime", "compilation")
        assert len(job_res["stderr"]) > 0
