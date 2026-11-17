"""Read the transaction receipts of the sampled markets over RPC (one request at a time,
cached on disk) and save a reduced copy per market to data/receipts/<conditionId>.json.

Reduction: keep only logs emitted by the two exchanges or by the pUSD contract, with
logIndex, address, topics and data, plus the transaction status. Nothing else in a receipt
is used by any number in the study.
Subsample rule (PREDICTIONS.md section 4): a market with more than 1,000 fill transactions
keeps the transactions whose hash, as an integer, is divisible by 2**k, k the smallest
integer with n / 2**k <= 1000.
Usage: fetch_receipts.py pilot | all
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rpc import rpc  # noqa: E402

DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")
KEEP = {a.lower() for a in (
    "0xE111180000d2663C0091e4f400237545B87B996B",   # exchange, standard
    "0xe2222d279d744050d28e00520010520000310F59",   # exchange, neg-risk
    "0xC011a7E12a19f7B1f670d46F03B03f3342E82DFB")}  # pUSD
CAP = 1000


def reduce_receipt(r):
    logs = [{"i": int(lg["logIndex"], 16), "a": lg["address"].lower(), "t": lg["topics"],
             "d": lg["data"]} for lg in r["logs"] if lg["address"].lower() in KEEP]
    return {"status": r["status"], "block": int(r["blockNumber"], 16), "logs": logs}


def pick_txs(txs):
    """Deterministic subsample: hash divisible by 2**k. Returns (kept hashes, k)."""
    k = 0
    while len(txs) / 2 ** k > CAP:
        k += 1
    return [t for t in sorted(txs) if int(t, 16) % 2 ** k == 0], k


def fetch_market(m):
    ix = json.load(open(os.path.join(DATA, "index", m["conditionId"] + ".json")))
    txs = sorted({t["transactionHash"] for t in ix["trades"]})
    kept, k = pick_txs(txs)
    recs = {t: rpc("eth_getTransactionReceipt", [t], reduce=reduce_receipt) for t in kept}
    out = {"conditionId": m["conditionId"], "n_index_txs": len(txs), "k": k, "receipts": recs}
    os.makedirs(os.path.join(DATA, "receipts"), exist_ok=True)
    with open(os.path.join(DATA, "receipts", m["conditionId"] + ".json"), "w") as f:
        json.dump(out, f)
    return len(kept), k


def main():
    sample = json.load(open(os.path.join(DATA, "sample.json")))
    if sys.argv[1] == "pilot":
        sample = [m for m in sample if m["pilot"]]
    for m in sample:
        path = os.path.join(DATA, "receipts", m["conditionId"] + ".json")
        if os.path.exists(path):
            continue
        n, k = fetch_market(m)
        print(m["conditionId"][:10], m["cell"], "fetched", n, "k", k, flush=True)


if __name__ == "__main__":
    main()
