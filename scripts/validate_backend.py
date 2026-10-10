"""Wait for an in-progress package install, then record real test exit status.

This helper is for development environments whose terminal completion events are
unreliable. It does not replace the documented pytest command.
"""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
required = ("pytest", "fastapi", "pydantic", "pymongo", "fitz", "docx", "sklearn", "multipart")
deadline = time.monotonic() + 900
while time.monotonic() < deadline:
    if all(importlib.util.find_spec(name) for name in required):
        break
    time.sleep(5)
else:
    (ROOT / "backend-test-status-check.txt").write_text("Dependencies did not finish installing within 15 minutes.", encoding="utf-8")
    sys.exit(2)

with (ROOT / "backend-tests-check.txt").open("w", encoding="utf-8") as output:
    result = subprocess.run([sys.executable, "-m", "pytest", "-q"], cwd=ROOT / "backend", stdout=output, stderr=subprocess.STDOUT)
(ROOT / "backend-test-status-check.txt").write_text(json.dumps({"pytest_exit_code": result.returncode}), encoding="utf-8")
sys.exit(result.returncode)