"""Offline: prediction scoring inputs and robustness checks. Reads data/results_all.json,
data/receipts/*.json, data/sample.json, data/frame_raw.jsonl. Writes data/scoring.json.
Usage: python3 -I code/score.py   (run compute.py all first)
"""
import json
import os
import statistics as st
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import compute as c  # noqa: E402
import apply_frame_rules as fr  # noqa: E402

DATA = c.DATA


def med(v):
    v = [x for x in v if x == x]
    return st.median(v) if v else None


def frame_counts():
    rows = [json.loads(line) for line in open(os.path.join(DATA, "frame_raw.jsonl"))]
    why = {}
    for m in rows:
        r = fr.classify(m) or "eligible"
        why[r] = why.get(r, 0) + 1
    return {"eligible": why["eligible"], "version_v2": why.get("version_v2", 0)}


def v_closer(res):
    """Where N1 and C differ most (f >= 0.15), which one is the venue figure closer to?"""
    out = {}
    for lo, hi, name in [(0, 0.05, "f<0.05"), (0.05, 0.15, "0.05<=f<0.15"), (0.15, 9, "f>=0.15")]:
        sub = [r for r in res if r["k"] == 0 and lo <= r["ratios"]["f"] < hi]
        out[name] = {"n": len(sub), "V/N1": med([r["v_ratios"]["V/N1"] for r in sub]),
                     "V/C": med([r["v_ratios"]["V/C"] for r in sub]),
                     "N1/C": med([r["ratios"]["N1/C"] for r in sub])}
    return out


def resample_check(sample, res):
    """Apply the 2**k hash rule to fully enumerated markets with >= 300 txs, k = 1 and 2,
    and compare N1/C with the full read. Tests the subsampling directly."""
    by = {r["conditionId"]: r for r in res}
    rows = []
    for m in sample:
        r = by[m["conditionId"]]
        if r["k"] != 0 or r["n_index_txs"] < 300:
            continue
        rec = json.load(open(os.path.join(DATA, "receipts", m["conditionId"] + ".json")))
        toks = {int(t) for t in json.loads(m["clobTokenIds"])}
        row = {"full": r["ratios"]["N1/C"]}
        for k in (1, 2):
            sub = {"k": k, "n_index_txs": 0, "receipts": {t: x for t, x in rec["receipts"].items()
                                                         if int(t, 16) % 2 ** k == 0}}
            s = c.market_result(m, toks, sub)
            row[f"k{k}"] = s["N1"] / s["C"]
        rows.append(row)
    return {"markets": len(rows),
            "median_abs_diff_k1": med([abs(x["k1"] - x["full"]) for x in rows]),
            "median_abs_diff_k2": med([abs(x["k2"] - x["full"]) for x in rows]),
            "median_signed_diff_k1": med([x["k1"] - x["full"] for x in rows]),
            "median_signed_diff_k2": med([x["k2"] - x["full"] for x in rows])}


def main():
    d = json.load(open(os.path.join(DATA, "results_all.json")))
    res, sample = d["markets"], json.load(open(os.path.join(DATA, "sample.json")))
    cn = d["counts"]
    n = cn["matches"]
    out = {"frame": frame_counts(),
           "P6_non_pure_comp_share": (cn["kinds"].get("mm", 0) + cn["kinds"].get("compmm", 0)) / n,
           "P7_mixed_share": cn["kinds"].get("compmm", 0) / n,
           "kind_shares": {k: v / n for k, v in cn["kinds"].items()},
           "P13_med_abs_OM_minus_Mk": med([abs(r["ratios"]["OM/C"] - r["ratios"]["Mk/C"]) for r in res]),
           "P18_negrisk_minus_standard_N1/C": med([r["ratios"]["N1/C"] for r in res if r["cell"].startswith("negrisk")])
           - med([r["ratios"]["N1/C"] for r in res if r["cell"].startswith("standard")]),
           "P19_W/C_minus_1_median": d["summary"]["W/C"]["median"] - 1,
           "V_closer_by_f": v_closer(res),
           "V_within_5pct_of": {k: sum(abs(r["v_ratios"][k] - 1) <= 0.05 for r in res if r["k"] == 0)
                                for k in ("V/N1", "V/OM", "V/C", "V/Mk")},
           "V_markets": sum(r["k"] == 0 for r in res),
           "resample": resample_check(sample, res)}
    json.dump(out, open(os.path.join(DATA, "scoring.json"), "w"), indent=1)
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
