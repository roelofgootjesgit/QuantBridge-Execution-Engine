from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import yaml

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from quantbridge.accounts.account_policy import AccountPolicy
from quantbridge.accounts.account_state_machine import AccountStateMachine
from quantbridge.router.account_selector import AccountSelector
from quantbridge.risk.account_limits import AccountLimits


def load_config(path: str) -> dict:
    cfg_path = Path(path)
    if not cfg_path.is_absolute():
        cfg_path = ROOT / cfg_path
    with open(cfg_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def parse_policies(config: dict) -> list[AccountPolicy]:
    policies: list[AccountPolicy] = []
    for raw in config.get("accounts", []) or []:
        limits_raw = raw.get("limits", {}) or {}
        limits = AccountLimits(
            daily_drawdown_limit_pct=float(limits_raw.get("daily_drawdown_limit_pct", 5.0)),
            total_drawdown_limit_pct=float(limits_raw.get("total_drawdown_limit_pct", 10.0)),
            max_open_risk_pct=float(limits_raw.get("max_open_risk_pct", 3.0)),
            max_risk_per_trade_pct=float(limits_raw.get("max_risk_per_trade_pct", 1.0)),
            max_concurrent_positions=int(limits_raw.get("max_concurrent_positions", 3)),
            symbol_exposure_limit_pct=float(limits_raw.get("symbol_exposure_limit_pct", 2.0)),
            min_units_per_trade=float(limits_raw.get("min_units_per_trade", 1.0)),
            max_units_per_trade=float(limits_raw.get("max_units_per_trade", 1000.0)),
        )
        policies.append(
            AccountPolicy(
                account_id=str(raw.get("account_id", "")),
                mode=str(raw.get("mode", "demo")),  # type: ignore[arg-type]
                enabled=bool(raw.get("enabled", True)),
                priority=int(raw.get("priority", 100)),
                sizing_multiplier=float(raw.get("sizing_multiplier", 1.0)),
                allowed_symbols=[str(s).upper() for s in (raw.get("allowed_symbols", []) or [])],
                limits=limits,
            )
        )
    return policies


def main() -> int:
    parser = argparse.ArgumentParser(description="Check account-aware routing selection.")
    parser.add_argument("--config", default="configs/accounts_baseline.yaml")
    parser.add_argument("--instrument", default="XAUUSD")
    parser.add_argument("--account-state-file", default="state/account_states.json")
    parser.add_argument("--pause-account", default=None, help="Account id to set paused before selection")
    parser.add_argument("--unhealthy-account", action="append", default=[])
    args = parser.parse_args()

    config = load_config(args.config)
    policies = parse_policies(config)
    machine = AccountStateMachine(path=args.account_state_file)

    if args.pause_account:
        machine.pause(account_id=str(args.pause_account), reason="orchestration_cli_pause")

    selector = AccountSelector(state_machine=machine)
    selection = selector.select(
        policies=policies,
        instrument=args.instrument,
        unhealthy_account_ids=args.unhealthy_account,
    )

    if selection is None:
        print(
            json.dumps(
                {
                    "selected": None,
                    "reason": "no_eligible_account",
                    "instrument": args.instrument.upper(),
                },
                indent=2,
            )
        )
        return 2

    print(
        json.dumps(
            {
                "selected": selection.account_id,
                "reason": selection.reason,
                "instrument": args.instrument.upper(),
                "sizing_multiplier": selection.selected_policy.sizing_multiplier,
                "mode": selection.selected_policy.mode,
                "skipped": selection.skipped,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
