"""Cached, throttled JSON-RPC and HTTP client for the shared public endpoints.

Rules for the shared public endpoints: at most two requests in flight (this client is sequential, so one),
back off on errors, cache every response on disk so nothing is fetched twice.
Standard library only.
"""
import hashlib
import json
import os
import time
import urllib.error
import urllib.request

CACHE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "cache")
ENDPOINTS = [
    "https://polygon-bor-rpc.publicnode.com",
    "https://polygon.drpc.org",
    "https://1rpc.io/matic",
]
GAP = 0.25  # seconds between requests
_last = [0.0]
_bad_until = {}  # endpoint -> time until which we skip it
_no_logs = set()  # endpoints that answered getLogs with HTTP 403: not used for getLogs again


class RpcError(Exception):
    """Deterministic JSON-RPC error (for example a result or range limit). Not retried."""


def _cache_path(kind, key):
    h = hashlib.sha256(key.encode()).hexdigest()
    d = os.path.join(CACHE, kind, h[:2])
    os.makedirs(d, exist_ok=True)
    return os.path.join(d, h + ".json")


def _post(url, payload, timeout=40):
    req = urllib.request.Request(
        url, data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json", "User-Agent": "research-client/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


def rpc(method, params, fresh=False, reduce=None):
    """JSON-RPC call with disk cache, endpoint rotation and exponential backoff.

    fresh=True skips the cache read (for eth_blockNumber); the result is still stored.
    reduce, if given, is applied to the result before it is cached and returned (used to
    keep only the logs a study needs from a full receipt).
    """
    key = json.dumps([method, params])
    path = _cache_path("rpc", key)
    if not fresh and os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    delay = 2.0
    for attempt in range(12):
        live = [e for e in ENDPOINTS if _bad_until.get(e, 0) < time.time()] or ENDPOINTS
        if method == "eth_getLogs":
            live = [e for e in live if e not in _no_logs] or live
        url = live[attempt % len(live)]
        time.sleep(max(0.0, GAP - (time.time() - _last[0])))
        _last[0] = time.time()
        try:
            out = _post(url, {"jsonrpc": "2.0", "id": 1, "method": method, "params": params})
            if "error" in out:
                msg = str(out["error"])[:300]
                if "usage limit" in msg.lower():  # plan quota used up: leave the endpoint for an hour
                    _bad_until[url] = time.time() + 3600
                    print(f"rpc quota {url}", flush=True)
                    continue
                transient = any(w in msg.lower() for w in ("rate", "too many requests", "capacity", "timeout", "busy"))
                if not transient:
                    raise RpcError(msg)
                raise RuntimeError(msg)
            result = reduce(out["result"]) if reduce else out["result"]
            with open(path, "w") as f:
                json.dump(result, f)
            return result
        except (urllib.error.URLError, RuntimeError, TimeoutError, OSError) as e:
            # Endpoints answer an oversized getLogs with HTTP 400/403. Two such answers
            # (two endpoints) mean "range too big": let the caller halve it, do not hammer.
            if method == "eth_getLogs" and isinstance(e, urllib.error.HTTPError):
                if e.code == 403:
                    _no_logs.add(url)  # blocked for getLogs: rotate away without sleeping
                    continue
                if e.code == 400 and attempt >= 1:
                    raise RpcError(f"HTTP 400 on getLogs (range too large)")
            if isinstance(e, urllib.error.HTTPError) and e.code == 403:
                _bad_until[url] = time.time() + 600  # blocked: leave it alone for 10 minutes
                continue
            _bad_until[url] = time.time() + delay
            print(f"rpc retry {attempt} {url} {type(e).__name__} {str(e)[:80]}", flush=True)
            time.sleep(delay)
            delay = min(delay * 2, 60)
    raise RuntimeError(f"rpc failed: {method}")


def http_get(url, headers=None):
    """GET JSON with disk cache and backoff (honours Retry-After on 429)."""
    path = _cache_path("http", url)
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    delay = 2.0
    for attempt in range(8):
        time.sleep(max(0.0, GAP - (time.time() - _last[0])))
        _last[0] = time.time()
        req = urllib.request.Request(url, headers=headers or {"User-Agent": "research-client/1.0"})
        try:
            with urllib.request.urlopen(req, timeout=40) as r:
                data = json.load(r)
            with open(path, "w") as f:
                json.dump(data, f)
            return data
        except urllib.error.HTTPError as e:
            wait = float(e.headers.get("Retry-After", delay)) if e.code == 429 else delay
            print(f"http {e.code} {url[:90]} wait {wait}", flush=True)
            if 400 <= e.code < 500 and e.code != 429:
                raise RuntimeError(f"HTTP {e.code}: {e.read()[:300]!r}")
            time.sleep(wait)
            delay = min(delay * 2, 60)
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            print(f"http retry {type(e).__name__}", flush=True)
            time.sleep(delay)
            delay = min(delay * 2, 60)
    raise RuntimeError(f"http failed: {url}")
