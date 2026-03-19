from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from quantbridge.ops.observability import summarize_jsonl_events


def main() -> int:
    parser = argparse.ArgumentParser(description="Summarize QuantBridge JSONL observability events.")
    parser.add_argument("--events-file", default="logs/events.jsonl")
    args = parser.parse_args()

    summary = summarize_jsonl_events(args.events_file)
    print(json.dumps(summary.__dict__, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
