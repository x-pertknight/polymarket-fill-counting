"""NOT PART OF THE OFFLINE RECOMPUTE. Do not re-run. It needs a live browser session and
the network. The recompute runs from saved files only (data/index/*.json and the cached
receipts); the index it produced is an input file, not something the recompute rebuilds.

Fetch the per-market fill index from the Polymarket Data API v2 /v2/trades.

Only reachable from a real browser (honest HTTP clients get ECONNRESET — see
DEVIATIONS.md 2026-11-17). Runs inside browser_exec, which pre-imports
new_tab / wait_for_load / js.

Writes data/index/<conditionId>.json per market, newest-first trades mapped to
{transactionHash, timestamp, asset}, window [startDate, closedTime] inclusive.
Pilot markets first, then the rest. Resumable: markets with a complete file are
skipped.
"""
import datetime
import json
import os
import time
import urllib.parse

DATA = "/Users/marco/dev/polymarket-fill-counting/data"
INDEX = os.path.join(DATA, "index")
SOURCE = "https://data-api.polymarket.com/v2/trades (browser)"
LIMIT = 500


def norm_ts(s):
    s = s.strip()
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    elif s.endswith("+00") or s.endswith("-00"):
        s = s + ":00"
    return s


def to_epoch(s):
    return int(datetime.datetime.fromisoformat(norm_ts(s)).timestamp())


def load_markets():
    with open(os.path.join(DATA, "sample.json")) as f:
        raw = json.load(f)
    # pilot first, keep file order inside each group
    ordered = [m for m in raw if m.get("pilot")] + [m for m in raw if not m.get("pilot")]
    return ordered


def _read_page(url):
    new_tab(url)
    wait_for_load()
    return js("document.body ? document.body.innerText : ''")


def fetch_pages(cid):
    """Follow cursor pagination to the end. Returns list of trade rows."""
    rows = []
    cursor = None
    while True:
        url = "https://data-api.polymarket.com/v2/trades?condition=%s&limit=%d" % (cid, LIMIT)
        if cursor:
            url += "&cursor=" + urllib.parse.quote(cursor)
        d = None
        for attempt in range(4):  # retry warm-up races / empty first loads
            try:
                d = json.loads(_read_page(url))
            except Exception:
                d = None
            if isinstance(d, dict) and "data" in d:
                break
            time.sleep(1.0 * (attempt + 1))
        if not isinstance(d, dict) or "data" not in d:
            return rows, False  # error object or unparseable page
        rows.extend(d.get("data", []))
        pg = d.get("pagination", {}) or {}
        if not pg.get("has_more"):
            return rows, True
        cursor = pg.get("next_cursor")
        if not cursor:
            return rows, False


def build_index(m):
    cid = m["conditionId"]
    start = to_epoch(m["startDate"])
    end = to_epoch(m["closedTime"])
    rows, complete = fetch_pages(cid)
    trades = []
    for r in rows:
        ts = r.get("timestamp")
        if ts is None or ts < start or ts > end:
            continue
        trades.append({
            "transactionHash": r.get("transaction_hash"),
            "timestamp": ts,
            "asset": str(r.get("token_id")),
        })
    # dedupe identical rows is not needed; keep one entry per fill
    doc = {
        "conditionId": cid,
        "source": SOURCE,
        "fetched_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "complete": complete,
        "trades": trades,
    }
    os.makedirs(INDEX, exist_ok=True)
    path = os.path.join(INDEX, cid + ".json")
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(doc, f)
    os.replace(tmp, path)
    return path, len(trades), complete


def is_done(m):
    p = os.path.join(INDEX, m["conditionId"] + ".json")
    if not os.path.exists(p):
        return False
    try:
        with open(p) as f:
            return bool(json.load(f).get("complete"))
    except Exception:
        return False


def run_batch(time_budget=240):
    markets = load_markets()
    remaining = [m for m in markets if not is_done(m)]
    print("total=%d done=%d remaining=%d" % (len(markets), len(markets) - len(remaining), len(remaining)))
    t0 = time.time()
    done_n = 0
    for m in remaining:
        if time.time() - t0 > time_budget:
            print("budget reached")
            break
        cid = m["conditionId"]
        try:
            path, n, complete = build_index(m)
            print("ok %s trades=%d complete=%s" % (cid, n, complete))
            done_n += 1
        except Exception as e:
            print("FAIL %s %s: %s" % (cid, type(e).__name__, str(e)[:120]))
    print("batch done=%d elapsed=%.1fs" % (done_n, time.time() - t0))
