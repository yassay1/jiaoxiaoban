"""Run lightweight architecture checks for the campus agent service."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PYCACHE_PREFIX = ROOT.parent / ".tmp_pycache"

CHECKS = [
    ["python", "-m", "compileall", "app"],
    [
        "pytest",
        "tests/test_graphs.py",
        "tests/test_assistant_planner_chain.py",
        "tests/test_assistant_plan_routing.py",
        "tests/test_professional_handoff.py",
        "tests/test_community_workflow_routing.py",
        "tests/test_frontend_action_mapping.py",
        "-q",
    ],
]


def run_check(command: list[str]) -> int:
    env = os.environ.copy()
    env["PYTHONPYCACHEPREFIX"] = str(PYCACHE_PREFIX)
    print(f"\n$ {' '.join(command)}", flush=True)
    completed = subprocess.run(command, cwd=ROOT, env=env, check=False)
    return completed.returncode


def main() -> int:
    for command in CHECKS:
        code = run_check(command)
        if code != 0:
            return code
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
