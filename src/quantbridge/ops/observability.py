from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class JsonlEventSink:
    path: str | Path
    source: str = "quantbridge"
    run_id: str = ""

    def __post_init__(self) -> None:
        self.path = Path(self.path)
        if not self.run_id:
            self.run_id = _utc_now_iso().replace(":", "").replace("-", "")

    def emit(self, event_type: str, payload: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        event = {
            "ts": _utc_now_iso(),
            "source": self.source,
            "run_id": self.run_id,
            "event_type": event_type,
            "payload": payload,
        }
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(event, sort_keys=True) + "\n")


@dataclass(frozen=True)
class EventSummary:
    total_events: int
    event_types: dict[str, int] = field(default_factory=dict)
    accounts: dict[str, int] = field(default_factory=dict)
    errors: int = 0


def summarize_jsonl_events(path: str | Path) -> EventSummary:
    event_counter: Counter[str] = Counter()
    account_counter: Counter[str] = Counter()
    errors = 0
    total = 0
    p = Path(path)
    if not p.exists():
        return EventSummary(total_events=0)

    for raw in p.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line:
            continue
        total += 1
        try:
            event = json.loads(line)
        except Exception:
            errors += 1
            continue
        event_type = str(event.get("event_type", "unknown"))
        event_counter[event_type] += 1
        payload = event.get("payload", {}) or {}
        account_id = str(payload.get("account_id", "")).strip()
        if account_id:
            account_counter[account_id] += 1
        if "error" in event_type or payload.get("error"):
            errors += 1

    return EventSummary(
        total_events=total,
        event_types=dict(event_counter),
        accounts=dict(account_counter),
        errors=errors,
    )

