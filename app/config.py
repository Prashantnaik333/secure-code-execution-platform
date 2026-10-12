"""
Configuration module for Secure Online Code Execution Platform.
Team 14 - Software Engineering Mini-Project
Defines system limits, supported languages, and sandbox parameters.
"""

from pathlib import Path
import os
import shutil

# Base Directories
BASE_DIR = Path(__file__).resolve().parent.parent
SANDBOX_BASE_DIR = BASE_DIR / ".sandbox_runtime"
STATIC_DIR = BASE_DIR / "static"
LOGS_DIR = BASE_DIR / "logs"

# Ensure runtime directories exist
SANDBOX_BASE_DIR.mkdir(parents=True, exist_ok=True)
LOGS_DIR.mkdir(parents=True, exist_ok=True)

# Numerical Defaults and Limits (SRS §3.4, SCEP-F-005, SCEP-F-006, SCEP-F-009)
MAX_CODE_SIZE_BYTES = 64 * 1024       # 64 KB
MAX_STDIN_SIZE_BYTES = 16 * 1024      # 16 KB
MAX_OUTPUT_SIZE_BYTES = 64 * 1024     # 64 KB
DEFAULT_TIMEOUT_SECONDS = 6.0          # 6.0 seconds
MAX_TIMEOUT_SECONDS = 10.0            # Upper cap for user-configurable timeout
MAX_MEMORY_MB = 256                   # 256 MB per job
MAX_CONCURRENT_JOBS = 5               # Maximum simultaneous executions
CLEANUP_GRACE_PERIOD_SEC = 1.0        # Grace period for child process cleanup

# Supported Languages Configuration
SUPPORTED_LANGUAGES = {
    "python": {
        "id": "python",
        "name": "Python 3.11",
        "extension": ".py",
        "is_compiled": False,
        "run_cmd": ["python", "{file}"],
        "default_code": (
            "# Python 3.11 Execution\n"
            "def main():\n"
            "    print('Hello from Secure Sandbox!')\n"
            "\n"
            "if __name__ == '__main__':\n"
            "    main()\n"
        ),
    },
    "javascript": {
        "id": "javascript",
        "name": "Node.js (JavaScript)",
        "extension": ".js",
        "is_compiled": False,
        "run_cmd": ["node", "{file}"],
        "default_code": (
            "// JavaScript (Node.js) Execution\n"
            "function main() {\n"
            "    console.log('Hello from Secure Sandbox!');\n"
            "}\n"
            "\n"
            "main();\n"
        ),
    },
    "c": {
        "id": "c",
        "name": "C (GCC 15.2)",
        "extension": ".c",
        "is_compiled": True,
        "compile_cmd": ["gcc", "-O2", "-Wall", "{file}", "-o", "{output}"],
        "binary_name": "program.exe" if os.name == "nt" else "program",
        "run_cmd": ["{output}"],
        "default_code": (
            "// C Execution\n"
            "#include <stdio.h>\n"
            "\n"
            "int main() {\n"
            "    printf(\"Hello from Secure Sandbox!\\n\");\n"
            "    return 0;\n"
            "}\n"
        ),
    },
    "cpp": {
        "id": "cpp",
        "name": "C++ (G++ 15.2)",
        "extension": ".cpp",
        "is_compiled": True,
        "compile_cmd": ["g++", "-O2", "-Wall", "{file}", "-o", "{output}"],
        "binary_name": "program.exe" if os.name == "nt" else "program",
        "run_cmd": ["{output}"],
        "default_code": (
            "// C++ Execution\n"
            "#include <iostream>\n"
            "\n"
            "int main() {\n"
            "    std::cout << \"Hello from Secure Sandbox!\" << std::endl;\n"
            "    return 0;\n"
            "}\n"
        ),
    },
    "java": {
        "id": "java",
        "name": "Java 26",
        "extension": ".java",
        "is_compiled": True,
        "fixed_source_name": "Main.java",
        "compile_cmd": ["javac", "{file}"],
        "run_cmd": ["java", "-cp", "{dir}", "Main"],
        "default_code": (
            "// Java Execution\n"
            "public class Main {\n"
            "    public static void main(String[] args) {\n"
            "        System.out.println(\"Hello from Secure Sandbox!\");\n"
            "    }\n"
            "}\n"
        ),
    },
}

# Environment variable keys permitted inside execution sandbox (least privilege / TC-SEC-01)
SAFE_ENV_KEYS = {
    "SYSTEMROOT", "WINDIR", "PATH", "PATHEXT", "TEMP", "TMP",
    "PYTHONIOENCODING", "PYTHONUTF8", "NODE_OPTIONS"
}

# Project Metadata
PROJECT_INFO = {
    "title": "Secure Online Code Execution Platform",
    "team": "Team 14",
    "members": [
        {"name": "Prathyush Gowda", "srn": "PES1UG24AM201", "role": "Coordinator & Integration"},
        {"name": "Pradyumn Bidari", "srn": "PES1UG24AM194", "role": "API & Validation"},
        {"name": "Prashant Devendra Naik", "srn": "PES1UG24AM199", "role": "Sandbox & Limits"},
        {"name": "Pradyun P Urs", "srn": "PES1UG24AM195", "role": "UI & Operational Monitoring"},
    ],
    "version": "1.0.0",
}
