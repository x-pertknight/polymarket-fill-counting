"""Build the sample frame from Gamma metadata only (no trades).

Server-side prefilter (see DEVIATIONS.md), then the rules in PREDICTIONS.md applied locally.
Writes data/frame_raw.jsonl (all fetched rows, trimmed) and data/frame.json (eligible).
"""
import json
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rpc import http_get  # noqa: E402

DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")
BASE = "https://gamma-api.polymarket.com/markets/keyset"
Q = ("closed=true&volume_num_min=1000&end_date_min=2026-09-20T00:00:00Z"
     "&end_date_max=2026-11-30T00:00:00Z&limit=100")
KEEP = ["conditionId", "slug", "startDate", "endDate", "closedTime", "volumeNum", "volumeClob",
        "version", "negRiskOther", "clobTokenIds", "events", "feeSchedule", "feesEnabled",
        "category", "acceptingOrders", "enableOrderBook"]


def parse_ts(s):
    if not s:
        return None
    s = s.replace(" ", "T").replace("+00", "+00:00") if "+" in s and ":" not in s[-3:] else s
    s = s.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(s).astimezone(timezone.utc)
    except ValueError:
        return None


def fetch_all():
    rows, cursor, pages = [], None, 0
    while True:
        url = f"{BASE}?{Q}" + (f"&after_cursor={cursor}" if cursor else "")
        d = http_get(url)
        for m in d["markets"]:
            rows.append({k: m.get(k) for k in KEEP})
        pages += 1
        if pages % 20 == 0:
            print("pages", pages, "rows", len(rows), flush=True)
        cursor = d.get("next_cursor")
        if not cursor or not d["markets"]:
            return rows


def main():
    rows = fetch_all()
    with open(os.path.join(DATA, "frame_raw.jsonl"), "w") as f:
        for r in rows:
            f.write(json.dumps(r, sort_keys=True) + "\n")
    print("fetched", len(rows))


if __name__ == "__main__":
    main()
