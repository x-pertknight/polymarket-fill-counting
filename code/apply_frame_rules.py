"""Apply the registered frame rules (PREDICTIONS.md section 4) to data/frame_raw.jsonl.

Writes data/frame.json (eligible markets, sorted by conditionId) and prints counts,
including how many candidates are excluded as version "v2" (prediction P22).
"""
import hashlib
import json
import os
from collections import Counter
from datetime import datetime, timezone

DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")
OCT1 = datetime(2026, 10, 1, tzinfo=timezone.utc)
NOV1 = datetime(2026, 11, 1, tzinfo=timezone.utc)
SEP1 = datetime(2026, 9, 1, tzinfo=timezone.utc)


def ts(s):
    """Parse Gamma timestamps such as '2026-10-03 14:00:00+00' or ISO with Z."""
    if not s:
        return None
    s = s.strip().replace(" ", "T").replace("Z", "+00:00")
    if s[-3] in "+-" and s[-2:].isdigit() and ":" not in s[-6:]:
        s += ":00"
    try:
        d = datetime.fromisoformat(s)
    except ValueError:
        return None
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)


def event_info(m):
    ev = (m.get("events") or [{}])[0]
    return str(ev.get("id")), bool(ev.get("negRisk"))


def classify(m):
    """Return (reason_excluded or None) for the registered rules, in order."""
    closed, start = ts(m["closedTime"]), ts(m["startDate"])
    if closed is None or not (OCT1 <= closed < NOV1):
        return "closedTime_not_october"
    if start is None or start < SEP1:
        return "start_before_sep1"
    if (m.get("volumeNum") or 0) < 1000:
        return "volume_below_1000"
    if (m.get("version") or "v1") != "v1":
        return "version_v2"
    return None


def band(v):
    return "small" if v < 25_000 else "medium" if v < 500_000 else "large"


def main():
    rows = [json.loads(line) for line in open(os.path.join(DATA, "frame_raw.jsonl"))]
    why = Counter()
    frame = []
    for m in rows:
        r = classify(m)
        why[r or "eligible"] += 1
        if r is None:
            eid, neg = event_info(m)
            frame.append({**{k: m[k] for k in ("conditionId", "slug", "startDate", "endDate",
                                              "closedTime", "volumeNum", "volumeClob", "version",
                                              "clobTokenIds", "feesEnabled", "category")},
                          "eventId": eid, "negRisk": neg, "band": band(m["volumeNum"])})
    frame.sort(key=lambda m: m["conditionId"].lower())
    # P22 denominator: candidates that met every rule except the version rule
    cand = why["eligible"] + why["version_v2"]
    print("raw rows", len(rows), dict(why))
    print("P22 share of candidates excluded as v2:", why["version_v2"], "/", cand)
    print("cells:", dict(Counter((f["negRisk"], f["band"]) for f in frame)))
    blob = json.dumps(frame, sort_keys=True, indent=0)
    with open(os.path.join(DATA, "frame.json"), "w") as f:
        f.write(blob)
    print("frame.json sha256", hashlib.sha256(blob.encode()).hexdigest())
    edge = [m for m in rows if classify(m) is None and ts(m["endDate"]) and
            (abs((ts(m["endDate"]) - datetime(2026, 9, 20, tzinfo=timezone.utc)).days) < 10 or
             abs((ts(m["endDate"]) - datetime(2026, 11, 30, tzinfo=timezone.utc)).days) < 10)]
    print("eligible markets with endDate within 10 days of a query edge:", len(edge))


if __name__ == "__main__":
    main()
