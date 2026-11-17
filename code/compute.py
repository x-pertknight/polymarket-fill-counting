"""Offline recompute of every study number from saved files only (stdlib).

Inputs: data/sample.json, data/receipts/<conditionId>.json (reduced receipts).
Outputs: data/results_<scope>.json with per-market sums, ratios and pilot/full summaries.
Usage: python3 -I code/compute.py pilot | all

Definitions are PREDICTIONS.md section 2. Side 0 = BUY, 1 = SELL (checked in sanity()).
"""
import json
import os
import statistics
import sys

DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")
OM_T = "0x174b3811690657c217184f89418266767c87e4805d09680c39fc9c031c0cab7c"
OF_T = "0xd543adfd945773f1a62f74f0ee55a5e3b9b1a28262980ba90b1a89f2ea84d8ee"
TR_T = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
PUSD = "0xc011a7e12a19f7b1f670d46f03b03f3342e82dfb"
SUMS = ["N1", "N2", "OM", "OMs", "T", "Mk", "W", "C", "C_incl", "Pay", "Recv", "fees",
        "comp_cash", "mm_shares"]


def words(data):
    h = data[2:]
    return [int(h[i:i + 64], 16) for i in range(0, len(h), 64)]


def addr(topic):
    return "0x" + topic[-40:]


def split_matches(logs):
    """Cut a receipt's logs into windows that each end with an OrdersMatched."""
    out, cur = [], []
    for lg in sorted(logs, key=lambda x: x["i"]):
        cur.append(lg)
        if lg["t"][0] == OM_T:
            out.append(cur)
            cur = []
    return out


def parse_row(lg):
    w = words(lg["d"])
    return {"side": w[0], "token": w[1], "mk": w[2], "tk": w[3], "fee": w[4],
            "maker": addr(lg["t"][2]), "taker": addr(lg["t"][3]), "ex": lg["a"]}


def cash(r):
    return r["mk"] if r["side"] == 0 else r["tk"]


def shares(r):
    return r["tk"] if r["side"] == 0 else r["mk"]


def receipt_cash(win, rows):
    """Net pUSD flow per maker-field trader in the window -> Pay, Recv (see PREDICTIONS 2)."""
    traders = {r["maker"] for r in rows}
    d = dict.fromkeys(traders, 0)
    for lg in win:
        if lg["a"] == PUSD and lg["t"][0] == TR_T and len(lg["t"]) == 3:
            v = words(lg["d"])[0]
            if addr(lg["t"][2]) in d:
                d[addr(lg["t"][2])] += v
            if addr(lg["t"][1]) in d:
                d[addr(lg["t"][1])] -= v
    pay = -sum(x for x in d.values() if x < 0)
    recv = sum(x for x in d.values() if x > 0)
    return pay, recv


def one_match(win, tokens):
    om = [lg for lg in win if lg["t"][0] == OM_T][-1]
    w = words(om["d"])
    if w[1] not in tokens:
        return None
    rows = [parse_row(lg) for lg in win if lg["t"][0] == OF_T and lg["a"] == om["a"]]
    taker = [r for r in rows if r["taker"] == om["a"]]
    maker = [r for r in rows if r["taker"] != om["a"]]
    pay, recv = receipt_cash(win, rows)
    fb = sum(r["fee"] for r in rows if r["side"] == 0)
    fs = sum(r["fee"] for r in rows if r["side"] == 1)
    c = max(pay - fb, recv + fs)
    T, Mk = sum(map(cash, taker)), sum(map(cash, maker))
    omc = w[2] if w[0] == 0 else w[3]
    tside = taker[0]["side"] if taker else w[0]
    comp = [r for r in maker if r["side"] != tside]
    mm = [r for r in maker if r["side"] == tside]
    kinds = ("comp" if comp else "") + ("mm" if mm else "")
    return {"N1": T + Mk, "N2": sum(map(shares, rows)), "OM": omc, "OMs": w[3] if w[0] == 0 else w[2],
            "T": T, "Mk": Mk, "W": T + 2 * Mk, "C": c, "C_incl": c + fb + fs, "Pay": pay,
            "Recv": recv, "fees": fb + fs, "comp_cash": sum(map(cash, comp)),
            "mm_shares": sum(map(shares, mm)), "kind": kinds,
            "self": any(r["maker"] in {t["maker"] for t in taker} for r in maker),
            "t_eq_om": T == omc, "nrows": len(rows),
            "p2_ok": abs(Mk - T) <= 1 if kinds == "comp" else None,
            "p4": (T + Mk) / c if kinds == "mm" and c else None}


def market_result(m, tokens, rec):
    tot = dict.fromkeys(SUMS, 0)
    kinds, selfs, t_ok, p2, p4, n, mixed_nonwin = {}, 0, 0, [], [], 0, 0
    for r in rec["receipts"].values():
        for win in split_matches(r["logs"]):
            x = one_match(win, tokens)
            if x is None:
                continue
            n += 1
            for k in SUMS:
                tot[k] += x[k]
            kinds[x["kind"]] = kinds.get(x["kind"], 0) + 1
            selfs += x["self"]
            t_ok += x["t_eq_om"]
            p2 += [x["p2_ok"]] if x["p2_ok"] is not None else []
            p4 += [x["p4"]] if x["p4"] is not None else []
    return {"conditionId": m["conditionId"], "cell": m["cell"], "matches": n, "kinds": kinds,
            "self_trades": selfs, "t_eq_om": t_ok, "p2_ok": sum(p2), "p2_n": len(p2),
            "p4_median": statistics.median(p4) if p4 else None,
            "k": rec["k"], "n_index_txs": rec["n_index_txs"],
            "volumeNum": m["volumeNum"], "volumeClob": m["volumeClob"], **tot}


def ratios(r):
    c = r["C"] or float("nan")
    f_den = r["comp_cash"] + r["mm_shares"]
    return {"N1/C": r["N1"] / c, "OM/C": r["OM"] / c, "Mk/C": r["Mk"] / c, "W/C": r["W"] / c,
            "T/C": r["T"] / c, "N2/OMs": r["N2"] / r["OMs"] if r["OMs"] else float("nan"),
            "fees/C": r["fees"] / c, "f": r["comp_cash"] / f_den if f_den else float("nan"),
            "|N1-(Pay+Recv)|/N1": abs(r["N1"] - (r["Pay"] + r["Recv"])) / r["N1"] if r["N1"] else float("nan")}


def spread(vals):
    v = sorted(x for x in vals if x == x)
    if not v:
        return None
    q = statistics.quantiles(v, n=4) if len(v) > 1 else [v[0]] * 3
    return {"n": len(v), "median": statistics.median(v), "p25": q[0], "p75": q[2], "min": v[0], "max": v[-1]}


def v_ratios(r):
    """Venue volume (Gamma volumeNum, USD) over each count, in USD. Meaningful when k == 0."""
    v = r["volumeNum"]
    return {"V/N1": v / (r["N1"] / 1e6), "V/OM": v / (r["OM"] / 1e6), "V/C": v / (r["C"] / 1e6),
            "V/Mk": v / (r["Mk"] / 1e6)}


def groups(res):
    """Spread of the headline ratios for each grouping used in the article."""
    keys = ["N1/C", "OM/C", "W/C", "Mk/C", "f"]
    cuts = {"all": lambda r: True,
            "standard": lambda r: r["cell"].startswith("standard"),
            "negrisk": lambda r: r["cell"].startswith("negrisk"),
            "small": lambda r: r["cell"].endswith("small"),
            "medium": lambda r: r["cell"].endswith("medium"),
            "large": lambda r: r["cell"].endswith("large"),
            "full_enumerated": lambda r: r["k"] == 0,
            "subsampled": lambda r: r["k"] > 0}
    for c in sorted({r["cell"] for r in res}):
        cuts[c] = lambda r, c=c: r["cell"] == c
    out = {}
    for name, fn in cuts.items():
        sub = [r for r in res if fn(r)]
        out[name] = {"markets": len(sub), **{k: spread([r["ratios"][k] for r in sub]) for k in keys}}
        full = [r for r in sub if r["k"] == 0]
        out[name]["V"] = {k: spread([v_ratios(r)[k] for r in full]) for k in ("V/N1", "V/OM", "V/C", "V/Mk")}
    return out


def counts(res):
    """Pooled counts used for the composition and identity predictions."""
    t = lambda k: sum(r[k] for r in res)
    kinds = {}
    for r in res:
        for k, v in r["kinds"].items():
            kinds[k] = kinds.get(k, 0) + v
    n = t("matches")
    return {"matches": n, "kinds": kinds, "t_eq_om": t("t_eq_om"), "p2_ok": t("p2_ok"), "p2_n": t("p2_n"),
            "self_trades": t("self_trades"), "zero_fee_markets": sum(r["fees"] == 0 for r in res),
            "P4_market_medians": spread([r["p4_median"] for r in res if r["p4_median"]]),
            "subsampled_markets": sum(r["k"] > 0 for r in res), "markets": len(res)}


def main():
    scope = sys.argv[1]
    sample = json.load(open(os.path.join(DATA, "sample.json")))
    if scope == "pilot":
        sample = [m for m in sample if m["pilot"]]
    res = []
    for m in sample:
        rec = json.load(open(os.path.join(DATA, "receipts", m["conditionId"] + ".json")))
        r = market_result(m, {int(t) for t in json.loads(m["clobTokenIds"])}, rec)
        r["ratios"] = ratios(r)
        res.append(r)
    keys = res[0]["ratios"].keys()
    summ = {k: spread([r["ratios"][k] for r in res]) for k in keys}
    summ["kill_stat_median_N1/C-1"] = statistics.median([r["ratios"]["N1/C"] - 1 for r in res])
    for r in res:
        r["v_ratios"] = v_ratios(r) if r["k"] == 0 else None
    with open(os.path.join(DATA, f"results_{scope}.json"), "w") as f:
        json.dump({"markets": res, "summary": summ, "groups": groups(res), "counts": counts(res)}, f, indent=1)
    print(json.dumps(summ, indent=1))


if __name__ == "__main__":
    main()
