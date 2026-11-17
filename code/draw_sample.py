"""Draw the registered sample (PREDICTIONS.md section 4) from data/frame.json.

Per cell (negRisk x volume band): order by sha256(conditionId + '|fill-counting-2026'),
take up to 10, at most 2 markets per Gamma event. No random number generator.
Pilot = first 3 per cell plus the 4th in each large cell.
"""
import hashlib
import json
import os

DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")
SALT = "|fill-counting-2026"


def key(m):
    return hashlib.sha256((m["conditionId"] + SALT).encode()).hexdigest()


def draw_cell(markets):
    taken, per_event = [], {}
    for m in sorted(markets, key=key):
        if per_event.get(m["eventId"], 0) >= 2:
            continue
        per_event[m["eventId"]] = per_event.get(m["eventId"], 0) + 1
        taken.append(m)
        if len(taken) == 10:
            break
    return taken


def main():
    frame = json.load(open(os.path.join(DATA, "frame.json")))
    sample = []
    for neg in (False, True):
        for band in ("small", "medium", "large"):
            cell = [m for m in frame if m["negRisk"] == neg and m["band"] == band]
            for rank, m in enumerate(draw_cell(cell), start=1):
                pilot = rank <= 3 or (band == "large" and rank == 4)
                sample.append({**m, "cell": f"{'negrisk' if neg else 'standard'}_{band}",
                               "rank": rank, "pilot": pilot})
    with open(os.path.join(DATA, "sample.json"), "w") as f:
        json.dump(sample, f, indent=1)
    print("sample", len(sample), "pilot", sum(s["pilot"] for s in sample))
    for s in sample:
        if s["pilot"]:
            print(s["cell"], s["rank"], round(s["volumeNum"]), s["startDate"][:10], s["closedTime"][:10])


if __name__ == "__main__":
    main()
