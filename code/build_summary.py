"""Verify the 60 index files and write data/index/_SUMMARY.json.

For each market: distinct transaction-hash count and the complete flag.
Also checks every trade entry carries only the three allowed fields
(no wallet address, no username).
"""
import json
import os
from pathlib import Path

# Data folder relative to this file, so the repo can live anywhere.
DATA = Path(__file__).resolve().parent.parent / "data"
INDEX = os.path.join(DATA, "index")
ALLOWED = {"transactionHash", "timestamp", "asset"}


def main():
    with open(os.path.join(DATA, "sample.json")) as f:
        sample = json.load(f)
    cids = [m["conditionId"] for m in sample]
    assert len(cids) == 60, "expected 60 markets, got %d" % len(cids)

    summary = {}
    problems = []
    for cid in cids:
        path = os.path.join(INDEX, cid + ".json")
        if not os.path.exists(path):
            problems.append("%s missing file" % cid)
            summary[cid] = {"distinct_transactions": None, "complete": False}
            continue
        with open(path) as f:
            doc = json.load(f)
        trades = doc.get("trades", [])
        hashes = set()
        for t in trades:
            if set(t.keys()) - ALLOWED:
                problems.append("%s leaked field %s" % (cid, set(t.keys()) - ALLOWED))
            h = t.get("transactionHash")
            if h:
                hashes.add(h)
        summary[cid] = {
            "distinct_transactions": len(hashes),
            "complete": bool(doc.get("complete")),
        }

    with open(os.path.join(INDEX, "_SUMMARY.json"), "w") as f:
        json.dump(summary, f, indent=1, sort_keys=True)

    complete_n = sum(1 for v in summary.values() if v["complete"])
    total_tx = sum(v["distinct_transactions"] or 0 for v in summary.values())
    print("markets=%d complete=%d incomplete=%d" % (len(summary), complete_n, len(summary) - complete_n))
    print("distinct transactions total=%d" % total_tx)
    print("problems:", problems if problems else "none")


if __name__ == "__main__":
    main()
