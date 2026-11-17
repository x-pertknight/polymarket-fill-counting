"""Independent check of the supplied trade index against a direct RPC log scan.

For each chosen market: scan OrdersMatched logs of its exchange over the market's life
(startDate to closedTime), keep those whose tokenId is one of the market's outcome tokens,
and compare the set of transaction hashes with data/index/<conditionId>.json.
OrdersMatched is emitted once per match and carries the taker order's tokenId in its data
(word 1), and every order in a match is on one of the market's two tokens, so this finds
every transaction that traded the market. Chain reads only; used for validation, not for
any reported number. Usage: validate_index.py <conditionId-prefix> [...]
"""
import json
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rpc import rpc, RpcError  # noqa: E402

DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")
EXCH = {"standard": "0xE111180000d2663C0091e4f400237545B87B996B",
        "negrisk": "0xe2222d279d744050d28e00520010520000310F59"}
CHUNK = 200  # blocks per getLogs request
ORDERS_MATCHED = "0x174b3811690657c217184f89418266767c87e4805d09680c39fc9c031c0cab7c"


def parse_ts(s):
    s = s.strip().replace(" ", "T").replace("Z", "+00:00")
    if s[-3] in "+-" and s[-2:].isdigit() and ":" not in s[-6:]:
        s += ":00"
    return int(datetime.fromisoformat(s).timestamp())


def block_ts(n):
    return int(rpc("eth_getBlockByNumber", [hex(n), False])["timestamp"], 16)


def first_block_at_or_after(ts):
    """Smallest block with timestamp >= ts.

    Start from the head, estimate the block time, then widen a bracket until it truly
    contains ts (so a wrong block-time guess cannot clip the answer), then bisect.
    """
    head = int(rpc("eth_blockNumber", [], fresh=True), 16)
    head_ts = block_ts(head)
    guess = max(1, head - int((head_ts - ts) / 1.5))
    lo, hi, step = guess - 5_000, guess + 5_000, 5_000
    while block_ts(lo) >= ts:
        lo, step = lo - step, step * 2
    while block_ts(hi) < ts:
        hi, step = hi + step, step * 2
        hi = min(hi, head)
    while lo < hi:
        mid = (lo + hi) // 2
        if block_ts(mid) < ts:
            lo = mid + 1
        else:
            hi = mid
    return lo


def scan(address, a, b, out):
    """getLogs for OrdersMatched on [a, b], halving the range on a limit error."""
    if a > b:
        return
    try:
        logs = rpc("eth_getLogs", [{"fromBlock": hex(a), "toBlock": hex(b), "address": address,
                                    "topics": [ORDERS_MATCHED]}])
    except RpcError:
        if a == b:
            raise
        mid = (a + b) // 2
        scan(address, a, mid, out)
        scan(address, mid + 1, b, out)
        return
    out.extend(logs)


def validate(m):
    ex = m["cell"].split("_")[0]
    tokens = {int(t) for t in json.loads(m["clobTokenIds"])}
    t0, t1 = parse_ts(m["startDate"]), parse_ts(m["closedTime"])
    a = first_block_at_or_after(t0)
    b = first_block_at_or_after(t1 + 1) - 1  # last block with timestamp <= t1
    logs = []
    for lo in range(a, b + 1, CHUNK):  # fixed-size chunks keep each response small
        scan(EXCH[ex], lo, min(lo + CHUNK - 1, b), logs)
    txs = {lg["transactionHash"] for lg in logs
           if int(lg["data"][2 + 64:2 + 128], 16) in tokens}
    ix = json.load(open(os.path.join(DATA, "index", m["conditionId"] + ".json")))
    idx = {t["transactionHash"] for t in ix["trades"]}
    return {"conditionId_prefix": m["conditionId"][:10], "cell": m["cell"], "blocks": [a, b],
            "logs_scanned": len(logs), "scan_txs": len(txs), "index_txs": len(idx),
            "missing_from_index": sorted(txs - idx), "extra_in_index": sorted(idx - txs)}


def main():
    sample = json.load(open(os.path.join(DATA, "sample.json")))
    results = []
    for prefix in sys.argv[1:]:
        m = next(s for s in sample if s["conditionId"].startswith(prefix))
        r = validate(m)
        print({k: (v if not isinstance(v, list) or len(v) < 6 else f"{len(v)} items") for k, v in r.items()},
              flush=True)
        results.append(r)
        with open(os.path.join(DATA, "index_validation.json"), "w") as f:
            json.dump(results, f, indent=1)


if __name__ == "__main__":
    main()
