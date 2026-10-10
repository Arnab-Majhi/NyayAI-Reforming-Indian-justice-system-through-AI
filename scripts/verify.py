"""Run reproducible local checks and retain exit codes despite shell integration issues.

Run with backend/.venv/Scripts/python.exe. Stop existing local servers first.
Browser tests start/stop their own servers via Playwright configuration.
"""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
NPM = shutil.which("npm.cmd") or shutil.which("npm")
env = {**os.environ, "PLAYWRIGHT_CHANNEL": os.getenv("PLAYWRIGHT_CHANNEL", "msedge")}
checks = [
    ("backend-final", [sys.executable, "-m", "pytest", "-q"], ROOT / "backend"),
    ("build-verified", [NPM, "run", "build"], ROOT / "frontend"),
    ("typecheck-verified", [NPM, "run", "typecheck"], ROOT / "frontend"),
    ("e2e-verified", [NPM, "run", "test:e2e"], ROOT / "frontend"),
]
results = {}
for name, command, cwd in checks:
    with (ROOT / f"{name}-check.txt").open("w", encoding="utf-8") as output:
        completed = subprocess.run(command, cwd=cwd, env=env, stdout=output, stderr=subprocess.STDOUT)
    results[name] = completed.returncode
    (ROOT / "verification-status-check.txt").write_text(json.dumps(results, indent=2), encoding="utf-8")
    if completed.returncode:
        sys.exit(completed.returncode)
print(json.dumps(results, indent=2))