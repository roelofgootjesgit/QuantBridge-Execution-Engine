from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Literal, Optional

AccountStatus = Literal["demo", "challenge", "funded", "paused", "breached", "disabled"]


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class AccountState:
    account_id: str
    status: AccountStatus
    reason: str = ""
    updated_at: str = field(default_factory=_utc_now_iso)


class AccountStateMachine:
    """Persisted account state transitions for routing + safety decisions."""

    def __init__(self, path: str | Path = "state/account_states.json") -> None:
        self.path = Path(path)

    def _load_raw(self) -> Dict[str, dict]:
        if not self.path.exists():
            return {}
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except Exception:
            return {}
        if not isinstance(data, dict):
            return {}
        return data

    def _save_raw(self, data: Dict[str, dict]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(f"{self.path.suffix}.tmp")
        tmp.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        tmp.replace(self.path)

    def get_state(self, account_id: str, default_status: AccountStatus = "demo") -> AccountState:
        raw = self._load_raw()
        entry = raw.get(str(account_id), {})
        status = str(entry.get("status", default_status))
        reason = str(entry.get("reason", ""))
        updated_at = str(entry.get("updated_at", _utc_now_iso()))
        return AccountState(
            account_id=str(account_id),
            status=status,  # type: ignore[arg-type]
            reason=reason,
            updated_at=updated_at,
        )

    def set_state(self, account_id: str, status: AccountStatus, reason: str = "") -> AccountState:
        raw = self._load_raw()
        state = AccountState(account_id=str(account_id), status=status, reason=reason)
        raw[str(account_id)] = {
            "status": state.status,
            "reason": state.reason,
            "updated_at": state.updated_at,
        }
        self._save_raw(raw)
        return state

    def pause(self, account_id: str, reason: str) -> AccountState:
        return self.set_state(account_id=account_id, status="paused", reason=reason)

    def breach(self, account_id: str, reason: str) -> AccountState:
        return self.set_state(account_id=account_id, status="breached", reason=reason)

    def resume(self, account_id: str, mode: Literal["demo", "challenge", "funded"], reason: str = "") -> AccountState:
        return self.set_state(account_id=account_id, status=mode, reason=reason)

    def is_eligible_for_trading(self, account_id: str, default_status: AccountStatus = "demo") -> bool:
        state = self.get_state(account_id=account_id, default_status=default_status)
        return state.status in {"demo", "challenge", "funded"}

    def get_pause_reason(self, account_id: str) -> Optional[str]:
        state = self.get_state(account_id=account_id)
        if state.status in {"paused", "breached", "disabled"}:
            return state.reason or state.status
        return None

