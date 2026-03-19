from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def run_step(name: str, command: list[str]) -> dict:
    started = time.time()
    result = subprocess.run(
        command,
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    duration_ms = int((time.time() - started) * 1000)
    return {
        "name": name,
        "command": " ".join(command),
        "exit_code": int(result.returncode),
        "duration_ms": duration_ms,
        "stdout": (result.stdout or "").strip(),
        "stderr": (result.stderr or "").strip(),
        "ok": result.returncode == 0,
    }


def main() -> int:
    python = sys.executable
    steps = [
        (
            "smoke_mock",
            [python, "scripts/ctrader_smoke.py", "--config", "configs/ctrader_icmarkets_demo.yaml", "--mode", "mock"],
        ),
        (
            "recovery_mock",
            [
                python,
                "scripts/recover_execution_state.py",
                "--config",
                "configs/ctrader_icmarkets_demo.yaml",
                "--mode",
                "mock",
                "--strategy",
                "OCLW",
            ],
        ),
        (
            "runtime_once_mock",
            [
                python,
                "scripts/run_runtime_control.py",
                "--config",
                "configs/ctrader_icmarkets_demo.yaml",
                "--mode",
                "mock",
                "--max-iterations",
                "1",
                "--account-status",
                "demo",
            ],
        ),
        (
            "order_lifecycle_mock",
            [
                python,
                "scripts/run_order_lifecycle_check.py",
                "--config",
                "configs/ctrader_icmarkets_demo.yaml",
                "--mode",
                "mock",
                "--direction",
                "BUY",
                "--sl",
                "2495",
                "--tp",
                "2510",
                "--close-after",
                "--account-status",
                "demo",
            ],
        ),
        (
            "orchestration_selector",
            [
                python,
                "scripts/run_account_orchestration_check.py",
                "--config",
                "configs/accounts_baseline.yaml",
                "--instrument",
                "XAUUSD",
            ],
        ),
        (
            "multi_account_single",
            [
                python,
                "scripts/run_multi_account_execution_check.py",
                "--config",
                "configs/accounts_baseline.yaml",
                "--instrument",
                "XAUUSD",
                "--routing-mode",
                "single",
                "--units",
                "100",
            ],
        ),
        (
            "multi_account_primary_backup",
            [
                python,
                "scripts/run_multi_account_execution_check.py",
                "--config",
                "configs/accounts_baseline.yaml",
                "--instrument",
                "XAUUSD",
                "--routing-mode",
                "primary_backup",
                "--units",
                "100",
            ],
        ),
        (
            "multi_account_fanout",
            [
                python,
                "scripts/run_multi_account_execution_check.py",
                "--config",
                "configs/accounts_baseline.yaml",
                "--instrument",
                "XAUUSD",
                "--routing-mode",
                "fanout",
                "--max-fanout-accounts",
                "2",
                "--units",
                "100",
            ],
        ),
    ]

    results = [run_step(name=name, command=cmd) for name, cmd in steps]
    failed = [r for r in results if not r["ok"]]
    output = {
        "suite": "quantbridge_regression_mock",
        "total_steps": len(results),
        "passed": len(results) - len(failed),
        "failed": len(failed),
        "ok": len(failed) == 0,
        "results": results,
    }
    print(json.dumps(output, indent=2))
    return 0 if len(failed) == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
