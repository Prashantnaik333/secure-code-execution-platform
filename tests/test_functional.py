"""
Functional Requirements Tests for Secure Online Code Execution Platform.
Implements test cases TC-F-01 to TC-F-07 from Software Test Plan (STP).
Traceable to SRS requirements SCEP-F-001, 002, 003, 007, 008, 010, 018.
"""

import time
import pytest
from app.job_manager import job_manager

def wait_for_job(client, job_id, token, max_wait=10.0):
    """Helper to poll job until completion."""
    start = time.time()
    while time.time() - start < max_wait:
        res = client.get(f"/api/jobs/{job_id}?token={token}")
        assert res.status_code == 200
        data = res.json()
        if data["status"] not in ("queued", "running"):
            return data
        time.sleep(0.1)
    raise TimeoutError(f"Job {job_id} did not finish within {max_wait}s")

class TestFunctional:

    def test_tc_f_01_submit_valid_small_program_python(self, client):
        """TC-F-01: Submit valid small Python program, verify acceptance and output."""
        payload = {
            "code": "print('Team 14 Functional Test Python')",
            "language": "python",
            "stdin": "",
        }
        res = client.post("/api/execute", json=payload)
        assert res.status_code == 202
        body = res.json()
        assert "jobId" in body
        assert "token" in body
        assert body["status"] in ("queued", "running")

        job_result = wait_for_job(client, body["jobId"], body["token"])
        assert job_result["status"] == "completed"
        assert "Team 14 Functional Test Python" in job_result["stdout"]
        assert job_result["exitCode"] == 0
        assert job_result["durationMs"] > 0

    def test_tc_f_01_submit_valid_c_program(self, client):
        """TC-F-01: Submit valid C program, verify compilation and output."""
        c_code = (
            "#include <stdio.h>\n"
            "int main() {\n"
            "    printf(\"Hello from C compiler!\\n\");\n"
            "    return 0;\n"
            "}\n"
        )
        payload = {"code": c_code, "language": "c", "timeoutSeconds": 8.0}
        res = client.post("/api/execute", json=payload)
        assert res.status_code == 202
        body = res.json()

        job_result = wait_for_job(client, body["jobId"], body["token"])
        assert job_result["status"] == "completed"
        assert "Hello from C compiler!" in job_result["stdout"]
        assert job_result["exitCode"] == 0

    def test_tc_f_01_submit_valid_cpp_program(self, client):
        """TC-F-01: Submit valid C++ program, verify compilation and output."""
        cpp_code = (
            "#include <iostream>\n"
            "int main() {\n"
            "    std::cout << \"Hello from C++ compiler!\" << std::endl;\n"
            "    return 0;\n"
            "}\n"
        )
        payload = {"code": cpp_code, "language": "cpp", "timeoutSeconds": 8.0}
        res = client.post("/api/execute", json=payload)
        assert res.status_code == 202
        body = res.json()

        job_result = wait_for_job(client, body["jobId"], body["token"])
        assert job_result["status"] == "completed"
        assert "Hello from C++ compiler!" in job_result["stdout"]
        assert job_result["exitCode"] == 0

    def test_tc_f_01_submit_valid_javascript_program(self, client):
        """TC-F-01: Submit valid JavaScript program, verify execution and output."""
        js_code = "console.log('Hello from Node.js!');"
        payload = {"code": js_code, "language": "javascript"}
        res = client.post("/api/execute", json=payload)
        assert res.status_code == 202
        body = res.json()

        job_result = wait_for_job(client, body["jobId"], body["token"])
        assert job_result["status"] == "completed"
        assert "Hello from Node.js!" in job_result["stdout"]
        assert job_result["exitCode"] == 0

    def test_tc_f_01_submit_valid_java_program(self, client):
        """TC-F-01: Submit valid Java program, verify compilation and output."""
        java_code = (
            "public class Main {\n"
            "    public static void main(String[] args) {\n"
            "        System.out.println(\"Hello from Java 26!\");\n"
            "    }\n"
            "}\n"
        )
        payload = {"code": java_code, "language": "java"}
        res = client.post("/api/execute", json=payload)
        assert res.status_code == 202
        body = res.json()

        job_result = wait_for_job(client, body["jobId"], body["token"])
        assert job_result["status"] == "completed"
        assert "Hello from Java 26!" in job_result["stdout"]
        assert job_result["exitCode"] == 0

    def test_tc_f_02_reject_invalid_requests(self, client):
        """TC-F-02: Submit missing code, invalid language, malformed requests -> clear 4xx."""
        # Empty code
        res1 = client.post("/api/execute", json={"code": "", "language": "python"})
        assert res1.status_code == 400
        assert res1.json()["category"] == "empty_code"

        # Missing code
        res2 = client.post("/api/execute", json={"language": "python"})
        assert res2.status_code == 400
        assert res2.json()["category"] == "missing_code"

        # Unsupported language
        res3 = client.post("/api/execute", json={"code": "print(1)", "language": "ruby"})
        assert res3.status_code == 400
        assert res3.json()["category"] == "unsupported_language"

    def test_tc_f_03_compilation_error_captured(self, client):
        """TC-F-03: Compilation error captured, binary not executed."""
        broken_c = (
            "#include <stdio.h>\n"
            "int main() {\n"
            "    broken_code_missing_semicolon\n"
            "    return 0;\n"
            "}\n"
        )
        res = client.post("/api/execute", json={"code": broken_c, "language": "c"})
        assert res.status_code == 202
        body = res.json()

        job_result = wait_for_job(client, body["jobId"], body["token"])
        assert job_result["status"] == "failed"
        assert job_result["errorCategory"] == "compilation"
        assert job_result["compileErrors"] is not None
        assert len(job_result["compileErrors"]) > 0
        assert job_result["stdout"] == ""

    def test_tc_f_04_separate_stdout_and_stderr(self, client):
        """TC-F-04: Verify stdout and stderr are captured into distinct streams."""
        py_code = (
            "import sys\n"
            "sys.stdout.write('OUT_STREAM_TEST\\n')\n"
            "sys.stderr.write('ERR_STREAM_TEST\\n')\n"
        )
        res = client.post("/api/execute", json={"code": py_code, "language": "python"})
        assert res.status_code == 202
        body = res.json()

        job_result = wait_for_job(client, body["jobId"], body["token"])
        assert job_result["status"] == "completed"
        assert "OUT_STREAM_TEST" in job_result["stdout"]
        assert "ERR_STREAM_TEST" in job_result["stderr"]
        assert "OUT_STREAM_TEST" not in job_result["stderr"]

    def test_tc_f_05_capture_exit_code_and_duration(self, client):
        """TC-F-05: Non-zero exit code and positive execution duration are reported."""
        py_code = "import sys\nsys.exit(42)\n"
        res = client.post("/api/execute", json={"code": py_code, "language": "python"})
        body = res.json()

        job_result = wait_for_job(client, body["jobId"], body["token"])
        assert job_result["status"] == "failed"
        assert job_result["exitCode"] == 42
        assert job_result["durationMs"] is not None
        assert job_result["durationMs"] >= 0

    def test_tc_f_06_job_lifecycle_states(self, client):
        """TC-F-06: Job transitions from queued/running to completed."""
        payload = {"code": "print('Lifecycle test')", "language": "python"}
        res = client.post("/api/execute", json=payload)
        body = res.json()
        assert body["status"] in ("queued", "running")

        job_result = wait_for_job(client, body["jobId"], body["token"])
        assert job_result["status"] == "completed"
        assert job_result["completedAt"] is not None

    def test_tc_f_07_structured_error_responses(self, client):
        """TC-F-07: Structured error responses are returned without leaking internal stack traces."""
        res = client.post("/api/execute", json={"code": "   ", "language": "python"})
        assert res.status_code == 400
        body = res.json()
        assert "error" in body
        assert "category" in body
        assert "Traceback" not in body["error"]
