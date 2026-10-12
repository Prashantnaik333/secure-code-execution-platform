/**
 * Secure Online Code Execution Platform - Frontend Client
 * Team 14 - Software Engineering Mini-Project
 */

// Generate or retrieve persistent client session ID
let clientId = localStorage.getItem("scep_client_id");
if (!clientId) {
  clientId = "client_" + Math.random().toString(36).substring(2, 10);
  localStorage.setItem("scep_client_id", clientId);
}

// Language templates and default filenames
const LANGUAGE_CONFIGS = {
  python: {
    fileName: "main.py",
    hello: `# Python 3.11 Execution\ndef main():\n    print("Hello from Secure Sandbox!")\n\nif __name__ == '__main__':\n    main()\n`,
    stdin: `# Reading from stdin\nimport sys\n\ndef main():\n    data = sys.stdin.read().strip()\n    print(f"Echo received input: {data}")\n\nif __name__ == '__main__':\n    main()\n`,
    fib: `# Fibonacci Calculation\ndef fib(n):\n    if n <= 1: return n\n    a, b = 0, 1\n    for _ in range(n - 1):\n        a, b = b, a + b\n    return b\n\nprint("Fibonacci(20) =", fib(20))\n`,
    timeout: `# [TC-LIM-01] Infinite Loop Timeout Test\nimport time\nprint("Starting infinite loop...")\nwhile True:\n    time.sleep(0.1)\n`,
    output_flood: `# [TC-LIM-03] Output Flood Test (Capped at 64KB)\nprint("Flooding stdout...")\nfor i in range(10000):\n    print(f"Flood line {i}: " + "X" * 50)\n`,
    compile_err: `# Syntax Error\ndef broken_func(\n    print("Missing closing paren")\n`,
    secret_probe: `# [TC-SEC-01] Host Secret & Environment Snooper Probe\nimport os\nprint("Checking environment variables in sandbox...")\nfor k, v in sorted(os.environ.items()):\n    print(f"{k} = {v}")\nprint("\\nNotice: Host credentials, AWS keys, and private tokens are stripped!")\n`,
    fs_probe: `# [TC-SEC-04] Filesystem Isolation Probe\nimport os\nprint("Current working directory:", os.getcwd())\ntry:\n    with open("../../Team14_Secure_Code_Execution_SRS.docx", "rb") as f:\n        print("WARNING: Leaked outside sandbox!")\nexcept Exception as e:\n    print(f"PASS: Host file access safely blocked: {e}")\n`,
  },
  javascript: {
    fileName: "main.js",
    hello: `// Node.js Execution\nconsole.log("Hello from Secure Sandbox!");\n`,
    stdin: `// Node.js stdin reading\nconst fs = require('fs');\ntry {\n    const input = fs.readFileSync(0, 'utf-8');\n    console.log("Echo received input:", input.trim());\n} catch (e) {\n    console.log("No input provided");\n}\n`,
    fib: `// Fibonacci in JavaScript\nfunction fib(n) {\n    let a = 0, b = 1;\n    for (let i = 2; i <= n; i++) {\n        let c = a + b;\n        a = b;\n        b = c;\n    }\n    return b;\n}\nconsole.log("Fibonacci(20) =", fib(20));\n`,
    timeout: `// [TC-LIM-01] Infinite Loop\nconsole.log("Spinning forever...");\nwhile (true) {}\n`,
    output_flood: `// [TC-LIM-03] Output Flood\nfor (let i = 0; i < 5000; i++) {\n    console.log("Flood chunk " + i + ": " + "Y".repeat(60));\n}\n`,
    compile_err: `// Syntax Error\nfunction broken( {\n    console.log("Unclosed");\n`,
    secret_probe: `// Inspect Process Environment\nconsole.log("Process ENV keys:", Object.keys(process.env).sort());\n`,
    fs_probe: `// Host filesystem probe\nconst fs = require('fs');\ntry {\n    fs.readFileSync('../../Team14_Secure_Code_Execution_SRS.docx');\n    console.log("FAIL: Leaked host file");\n} catch (e) {\n    console.log("PASS: Blocked or prevented host access:", e.message);\n}\n`,
  },
  c: {
    fileName: "main.c",
    hello: `// C Execution\n#include <stdio.h>\n\nint main() {\n    printf("Hello from Secure Sandbox!\\n");\n    return 0;\n}\n`,
    stdin: `// C Stdin Echo\n#include <stdio.h>\n\nint main() {\n    char buffer[256];\n    if (fgets(buffer, sizeof(buffer), stdin)) {\n        printf("Echo received input: %s\\n", buffer);\n    }\n    return 0;\n}\n`,
    fib: `// C Fibonacci\n#include <stdio.h>\n\nlong long fib(int n) {\n    long long a = 0, b = 1;\n    for (int i = 2; i <= n; i++) {\n        long long c = a + b;\n        a = b;\n        b = c;\n    }\n    return b;\n}\n\nint main() {\n    printf("Fibonacci(20) = %lld\\n", fib(20));\n    return 0;\n}\n`,
    timeout: `// [TC-LIM-01] Infinite Loop\n#include <stdio.h>\n\nint main() {\n    printf("Infinite C loop running...\\n");\n    fflush(stdout);\n    while (1) {}\n    return 0;\n}\n`,
    output_flood: `// [TC-LIM-03] Output Flood\n#include <stdio.h>\n\nint main() {\n    for (int i = 0; i < 5000; i++) {\n        printf("Flood line %d: ABCDEFGHIJKLMNOPQRSTUVWXYZ\\n", i);\n    }\n    return 0;\n}\n`,
    compile_err: `// [TC-F-03] Compilation Syntax Error\n#include <stdio.h>\n\nint main() {\n    printf("Missing semicolon")\n    return 0\n}\n`,
    secret_probe: `// C Environment Probe\n#include <stdio.h>\n#include <stdlib.h>\n\nint main() {\n    printf("Sandbox temp: %s\\n", getenv("TEMP"));\n    return 0;\n}\n`,
    fs_probe: `// C Filesystem Probe\n#include <stdio.h>\n\nint main() {\n    FILE *f = fopen("../../Team14_Secure_Code_Execution_SRS.docx", "r");\n    if (f) {\n        printf("FAIL: Host file opened!\\n");\n        fclose(f);\n    } else {\n        printf("PASS: Host file not accessible.\\n");\n    }\n    return 0;\n}\n`,
  },
  cpp: {
    fileName: "main.cpp",
    hello: `// C++ Execution\n#include <iostream>\n\nint main() {\n    std::cout << "Hello from Secure Sandbox!" << std::endl;\n    return 0;\n}\n`,
    stdin: `// C++ Stdin Echo\n#include <iostream>\n#include <string>\n\nint main() {\n    std::string input;\n    if (std::getline(std::cin, input)) {\n        std::cout << "Echo received input: " << input << std::endl;\n    }\n    return 0;\n}\n`,
    fib: `// C++ Fibonacci\n#include <iostream>\n\nlong long fib(int n) {\n    long long a = 0, b = 1;\n    for (int i = 2; i <= n; i++) {\n        long long c = a + b;\n        a = b;\n        b = c;\n    }\n    return b;\n}\n\nint main() {\n    std::cout << "Fibonacci(20) = " << fib(20) << std::endl;\n    return 0;\n}\n`,
    timeout: `// [TC-LIM-01] Infinite Loop\n#include <iostream>\n\nint main() {\n    std::cout << "C++ infinite loop..." << std::endl;\n    while (true) {}\n    return 0;\n}\n`,
    output_flood: `// [TC-LIM-03] Output Flood\n#include <iostream>\n\nint main() {\n    for (int i = 0; i < 5000; ++i) {\n        std::cout << "Flood line " << i << ": 12345678901234567890\\n";\n    }\n    return 0;\n}\n`,
    compile_err: `// [TC-F-03] Compilation Syntax Error\n#include <iostream>\n\nint main() {\n    std::cout << "Missing semicolon" << std::endl\n    return 0;\n}\n`,
    secret_probe: `// C++ Environment Probe\n#include <iostream>\n#include <cstdlib>\n\nint main() {\n    std::cout << "TEMP: " << (std::getenv("TEMP") ? std::getenv("TEMP") : "None") << std::endl;\n    return 0;\n}\n`,
    fs_probe: `// C++ Filesystem Probe\n#include <iostream>\n#include <fstream>\n\nint main() {\n    std::ifstream file("../../Team14_Secure_Code_Execution_SRS.docx");\n    if (file.is_open()) {\n        std::cout << "FAIL: Opened host file!" << std::endl;\n    } else {\n        std::cout << "PASS: Host file blocked." << std::endl;\n    }\n    return 0;\n}\n`,
  },
  java: {
    fileName: "Main.java",
    hello: `// Java Execution\npublic class Main {\n    public static void main(String[] args) {\n        System.out.println("Hello from Secure Sandbox!");\n    }\n}\n`,
    stdin: `// Java Stdin Echo\nimport java.util.Scanner;\n\npublic class Main {\n    public static void main(String[] args) {\n        Scanner sc = new Scanner(System.in);\n        if (sc.hasNextLine()) {\n            System.out.println("Echo received input: " + sc.nextLine());\n        }\n    }\n}\n`,
    fib: `// Java Fibonacci\npublic class Main {\n    public static void main(String[] args) {\n        long a = 0, b = 1;\n        for (int i = 2; i <= 20; i++) {\n            long c = a + b;\n            a = b;\n            b = c;\n        }\n        System.out.println("Fibonacci(20) = " + b);\n    }\n}\n`,
    timeout: `// [TC-LIM-01] Infinite Loop\npublic class Main {\n    public static void main(String[] args) {\n        System.out.println("Java infinite loop starting...");\n        while (true) {}\n    }\n}\n`,
    output_flood: `// [TC-LIM-03] Output Flood\npublic class Main {\n    public static void main(String[] args) {\n        for (int i = 0; i < 5000; i++) {\n            System.out.println("Java flood line " + i + ": ##################");\n        }\n    }\n}\n`,
    compile_err: `// [TC-F-03] Compilation Syntax Error\npublic class Main {\n    public static void main(String[] args) {\n        System.out.println("Broken syntax")\n    }\n}\n`,
    secret_probe: `// Java Environment Probe\npublic class Main {\n    public static void main(String[] args) {\n        System.out.println("Java Temp Dir: " + System.getProperty("java.io.tmpdir"));\n    }\n}\n`,
    fs_probe: `// Java Filesystem Probe\nimport java.io.File;\n\npublic class Main {\n    public static void main(String[] args) {\n        File f = new File("../../Team14_Secure_Code_Execution_SRS.docx");\n        if (f.exists() && f.canRead()) {\n            System.out.println("FAIL: Host file accessible!");\n        } else {\n            System.out.println("PASS: Host file blocked or not found.");\n        }\n    }\n}\n`,
  },
};

// DOM Elements
const languageSelect = document.getElementById("languageSelect");
const presetSelect = document.getElementById("presetSelect");
const codeEditor = document.getElementById("codeEditor");
const lineNumbers = document.getElementById("lineNumbers");
const fileNameLabel = document.getElementById("fileNameLabel");
const btnRun = document.getElementById("btnRun");
const btnResetCode = document.getElementById("btnResetCode");
const btnClearCode = document.getElementById("btnClearCode");
const btnToggleStdin = document.getElementById("btnToggleStdin");
const stdinDrawer = document.getElementById("stdinDrawer");
const stdinInput = document.getElementById("stdinInput");
const btnCloseStdin = document.getElementById("btnCloseStdin");
const stdinBadge = document.getElementById("stdinBadge");

// Output elements
const outputTabs = document.querySelectorAll(".output-tab");
const outputStdout = document.getElementById("outputStdout");
const outputStderr = document.getElementById("outputStderr");
const outputCompiler = document.getElementById("outputCompiler");
const compilerTabBtn = document.getElementById("compilerTabBtn");
const btnClearOutput = document.getElementById("btnClearOutput");

// Status banner elements
const statusBanner = document.getElementById("statusBanner");
const statusIcon = document.getElementById("statusIcon");
const statusText = document.getElementById("statusText");
const metricDuration = document.getElementById("metricDuration");
const metricExitCode = document.getElementById("metricExitCode");

// Modal elements
const btnHealth = document.getElementById("btnHealth");
const healthModal = document.getElementById("healthModal");
const btnCloseHealthModal = document.getElementById("btnCloseHealthModal");
const healthModalBody = document.getElementById("healthModalBody");

const btnHistory = document.getElementById("btnHistory");
const historyModal = document.getElementById("historyModal");
const btnCloseHistoryModal = document.getElementById("btnCloseHistoryModal");
const historyModalBody = document.getElementById("historyModalBody");

// Line numbers sync
function updateLineNumbers() {
  const lines = codeEditor.value.split("\n").length;
  let numbersHtml = "";
  for (let i = 1; i <= lines; i++) {
    numbersHtml += i + "<br>";
  }
  lineNumbers.innerHTML = numbersHtml;
}

codeEditor.addEventListener("input", updateLineNumbers);
codeEditor.addEventListener("scroll", () => {
  lineNumbers.scrollTop = codeEditor.scrollTop;
});

// Tab indentation support
codeEditor.addEventListener("keydown", (e) => {
  if (e.key === "Tab") {
    e.preventDefault();
    const start = codeEditor.selectionStart;
    const end = codeEditor.selectionEnd;
    codeEditor.value = codeEditor.value.substring(0, start) + "    " + codeEditor.value.substring(end);
    codeEditor.selectionStart = codeEditor.selectionEnd = start + 4;
    updateLineNumbers();
  }
  // Ctrl+Enter or Cmd+Enter to run
  if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
    e.preventDefault();
    executeCode();
  }
});

// Language and Preset Change Handlers
function loadCodeForCurrentSelection() {
  const lang = languageSelect.value;
  const preset = presetSelect.value;
  const cfg = LANGUAGE_CONFIGS[lang];
  fileNameLabel.textContent = cfg.fileName;

  if (preset === "stdin") {
    stdinInput.value = "Hello World from Stdin Test 123";
    stdinDrawer.classList.remove("collapsed");
    stdinBadge.textContent = "Stdin (Configured)";
  } else {
    stdinBadge.textContent = stdinInput.value.trim() ? "Stdin (Active)" : "Stdin (Empty)";
  }

  codeEditor.value = cfg[preset] || cfg.hello;
  updateLineNumbers();

  // Show/hide compiler tab for compiled languages
  if (lang === "c" || lang === "cpp" || lang === "java") {
    compilerTabBtn.style.display = "inline-block";
  } else {
    compilerTabBtn.style.display = "none";
  }
}

languageSelect.addEventListener("change", loadCodeForCurrentSelection);
presetSelect.addEventListener("change", loadCodeForCurrentSelection);

btnResetCode.addEventListener("click", loadCodeForCurrentSelection);
btnClearCode.addEventListener("click", () => {
  codeEditor.value = "";
  updateLineNumbers();
});

// Stdin Drawer Toggling
btnToggleStdin.addEventListener("click", () => {
  stdinDrawer.classList.toggle("collapsed");
});
btnCloseStdin.addEventListener("click", () => {
  stdinDrawer.classList.add("collapsed");
});
stdinInput.addEventListener("input", () => {
  stdinBadge.textContent = stdinInput.value.trim() ? "Stdin (Active)" : "Stdin (Empty)";
});

// Output Tab Switching
outputTabs.forEach((tab) => {
  tab.addEventListener("click", () => {
    outputTabs.forEach((t) => t.classList.remove("active"));
    tab.classList.add("active");

    const target = tab.getAttribute("data-tab");
    outputStdout.style.display = target === "stdout" ? "block" : "none";
    outputStderr.style.display = target === "stderr" ? "block" : "none";
    outputCompiler.style.display = target === "compiler" ? "block" : "none";
  });
});

btnClearOutput.addEventListener("click", () => {
  outputStdout.textContent = "";
  outputStderr.textContent = "";
  outputCompiler.textContent = "";
  statusBanner.className = "status-banner idle";
  statusIcon.textContent = "⚪";
  statusText.textContent = "Ready";
  metricDuration.style.display = "none";
  metricExitCode.style.display = "none";
});

// Status Banner Update
function setExecutionStatus(state, msg, duration = null, exitCode = null) {
  statusBanner.className = `status-banner ${state}`;
  if (state === "running" || state === "queued") {
    statusIcon.textContent = "⏳";
  } else if (state === "completed") {
    statusIcon.textContent = "✅";
  } else if (state === "timed_out") {
    statusIcon.textContent = "⏰";
  } else if (state === "failed") {
    statusIcon.textContent = "❌";
  } else {
    statusIcon.textContent = "⚪";
  }
  statusText.textContent = msg;

  if (duration !== null) {
    metricDuration.style.display = "inline-block";
    metricDuration.innerHTML = `Duration: <strong>${duration}ms</strong>`;
  } else {
    metricDuration.style.display = "none";
  }

  if (exitCode !== null) {
    metricExitCode.style.display = "inline-block";
    metricExitCode.innerHTML = `Exit: <strong>${exitCode}</strong>`;
  } else {
    metricExitCode.style.display = "none";
  }
}

// Code Execution Flow
async function executeCode() {
  const code = codeEditor.value;
  const lang = languageSelect.value;
  const stdinVal = stdinInput.value;

  if (!code.trim()) {
    alert("Please write or paste code before executing.");
    return;
  }

  btnRun.disabled = true;
  btnRun.classList.add("running");
  setExecutionStatus("running", "Submitting code to sandbox...");

  outputStdout.textContent = "";
  outputStderr.textContent = "";
  outputCompiler.textContent = "";

  try {
    const res = await fetch("/api/execute", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        code: code,
        language: lang,
        stdin: stdinVal,
        clientId: clientId,
      }),
    });

    const submitData = await res.json();
    if (!res.ok) {
      setExecutionStatus("failed", `Submission error: ${submitData.error || "Rejected"}`);
      outputStderr.textContent = JSON.stringify(submitData, null, 2);
      switchTab("stderr");
      btnRun.disabled = false;
      return;
    }

    const jobId = submitData.jobId;
    const token = submitData.token;
    setExecutionStatus("running", `Executing in isolated sandbox (Job: ${jobId.substring(0, 8)}...)...`);

    // Poll for completion
    let attempts = 0;
    const maxAttempts = 100;
    const pollInterval = 150;

    const pollTimer = setInterval(async () => {
      attempts++;
      try {
        const jobRes = await fetch(`/api/jobs/${jobId}?token=${token}`);
        if (!jobRes.ok) {
          clearInterval(pollTimer);
          setExecutionStatus("failed", "Failed to retrieve job status");
          btnRun.disabled = false;
          return;
        }

        const job = await jobRes.json();
        if (job.status === "running" || job.status === "queued") {
          if (attempts >= maxAttempts) {
            clearInterval(pollTimer);
            setExecutionStatus("failed", "Polling timed out");
            btnRun.disabled = false;
          }
          return;
        }

        // Job has concluded
        clearInterval(pollTimer);
        btnRun.disabled = false;

        outputStdout.textContent = job.stdout || "(No standard output generated)";
        outputStderr.textContent = job.stderr || "(No errors written to stderr)";
        outputCompiler.textContent = job.compileErrors || "(Compilation succeeded with zero warnings)";

        let stateMsg = `Execution ${job.status}`;
        if (job.status === "timed_out") stateMsg = "Execution Timed Out (Wall-clock limit reached)";
        if (job.status === "failed" && job.errorCategory === "compilation") {
          stateMsg = "Compilation Failed";
          switchTab("compiler");
        } else if (job.stderr && job.stderr.trim()) {
          switchTab("stderr");
        } else {
          switchTab("stdout");
        }

        setExecutionStatus(job.status, stateMsg, job.durationMs, job.exitCode);
      } catch (err) {
        clearInterval(pollTimer);
        btnRun.disabled = false;
        setExecutionStatus("failed", "Network communication error");
      }
    }, pollInterval);
  } catch (err) {
    btnRun.disabled = false;
    setExecutionStatus("failed", `Network error: ${err.message}`);
  }
}

function switchTab(tabName) {
  outputTabs.forEach((t) => {
    if (t.getAttribute("data-tab") === tabName) {
      t.click();
    }
  });
}

btnRun.addEventListener("click", executeCode);

// Modals: System Health & Info
btnHealth.addEventListener("click", async () => {
  healthModal.style.display = "flex";
  healthModalBody.innerHTML = "<p>Loading status...</p>";
  try {
    const res = await fetch("/api/health");
    const data = await res.json();
    healthModalBody.innerHTML = `
      <h3>Platform & Team Information</h3>
      <p><strong>Project:</strong> Secure Online Code Execution Platform (Team 14)</p>
      <p><strong>System Status:</strong> <span style="color:#3fb950; font-weight:600;">${data.status.toUpperCase()}</span> (Worker Ready: ${data.workerReady})</p>
      <p><strong>System Uptime:</strong> ${data.uptimeSeconds} seconds</p>
      
      <h3>Team 14 Members</h3>
      <table>
        <thead>
          <tr><th>Name</th><th>SRN</th><th>Role</th></tr>
        </thead>
        <tbody>
          <tr><td>Prathyush Gowda</td><td>PES1UG24AM201</td><td>Coordinator & Integration</td></tr>
          <tr><td>Pradyumn Bidari</td><td>PES1UG24AM194</td><td>API & Validation</td></tr>
          <tr><td>Prashant Devendra Naik</td><td>PES1UG24AM199</td><td>Sandbox & Limits</td></tr>
          <tr><td>Pradyun P Urs</td><td>PES1UG24AM195</td><td>UI & Operational Monitoring</td></tr>
        </tbody>
      </table>

      <h3>Sandbox Security & Enforced Limits</h3>
      <table>
        <thead>
          <tr><th>Parameter</th><th>Quota Limit</th></tr>
        </thead>
        <tbody>
          <tr><td>Max Source Code Size</td><td>${(data.limits.maxCodeSize / 1024)} KB</td></tr>
          <tr><td>Max Standard Input Size</td><td>${(data.limits.maxStdinSize / 1024)} KB</td></tr>
          <tr><td>Max Output Buffer Limit</td><td>${(data.limits.maxOutputSize / 1024)} KB</td></tr>
          <tr><td>Wall-Clock Execution Timeout</td><td>${data.limits.defaultTimeoutSeconds}s (Max ${data.limits.maxTimeoutSeconds}s)</td></tr>
          <tr><td>Memory Limit</td><td>${data.limits.maxMemoryMb} MB</td></tr>
          <tr><td>Environment Policy</td><td>Least-privilege safe allowlist; all secrets stripped</td></tr>
          <tr><td>Process Boundary</td><td>Subprocess tree kill on timeout & completion</td></tr>
        </tbody>
      </table>
    `;
  } catch (err) {
    healthModalBody.innerHTML = `<p style="color:#f85149">Failed to fetch health info: ${err.message}</p>`;
  }
});

btnCloseHealthModal.addEventListener("click", () => {
  healthModal.style.display = "none";
});

// Modal: History
btnHistory.addEventListener("click", async () => {
  historyModal.style.display = "flex";
  historyModalBody.innerHTML = "<p>Loading session history...</p>";
  try {
    const res = await fetch(`/api/history?clientId=${clientId}`);
    const data = await res.json();
    if (!data.history || data.history.length === 0) {
      historyModalBody.innerHTML = "<p>No jobs submitted during this session.</p>";
      return;
    }
    let rows = data.history.map((j) => `
      <tr>
        <td><code>${j.jobId.substring(0, 8)}...</code></td>
        <td><strong>${j.language}</strong></td>
        <td><span class="status-badge status-${j.status}">${j.status}</span></td>
        <td>${j.durationMs !== null ? j.durationMs + "ms" : "-"}</td>
        <td>${j.exitCode !== null ? j.exitCode : "-"}</td>
      </tr>
    `).join("");

    historyModalBody.innerHTML = `
      <table>
        <thead>
          <tr><th>Job ID</th><th>Language</th><th>Status</th><th>Duration</th><th>Exit Code</th></tr>
        </thead>
        <tbody>
          ${rows}
        </tbody>
      </table>
    `;
  } catch (err) {
    historyModalBody.innerHTML = `<p style="color:#f85149">Failed to fetch history: ${err.message}</p>`;
  }
});

btnCloseHistoryModal.addEventListener("click", () => {
  historyModal.style.display = "none";
});

// Close modal on outside click
window.addEventListener("click", (e) => {
  if (e.target === healthModal) healthModal.style.display = "none";
  if (e.target === historyModal) historyModal.style.display = "none";
});

// Initial boot
loadCodeForCurrentSelection();
