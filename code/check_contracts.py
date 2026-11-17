"""Step 1 checks before any sampling: pUSD decimals, V2 event topic0 values,
live logs on both exchanges, and which adapter addresses hold code.

Writes data/contract_checks.json. Chain reads only; no market data.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from keccak_lib import keccak256  # noqa: E402
from rpc import rpc  # noqa: E402

PUSD = "0xC011a7E12a19f7B1f670d46F03B03f3342E82DFB"
EXCHANGES = {
    "standard": "0xE111180000d2663C0091e4f400237545B87B996B",
    "negrisk": "0xe2222d279d744050d28e00520010520000310F59",
}
EXCHANGE_V3 = "0xe3333700cA9d93003F00f0F71f8515005F6c00Aa"
ADAPTERS = {
    "readme_ctf": "0xADa100874d00e3331D00F2007a9c336a65009718",
    "docs_ctf": "0xAdA100Db00Ca00073811820692005400218FcE1f",
    "readme_negrisk": "0xAdA200001000ef00D07553cEE7006808F895c6F1",
    "docs_negrisk": "0xadA2005600Dec949baf300f4C6120000bDB6eAab",
}
SIGS = {
    "OrderFilled_v2": "OrderFilled(bytes32,address,address,uint8,uint256,uint256,uint256,uint256,bytes32,bytes32)",
    "OrdersMatched_v2": "OrdersMatched(bytes32,address,uint8,uint256,uint256,uint256)",
    "FeeCharged": "FeeCharged(address,uint256)",
    "OrderFilled_v1": "OrderFilled(bytes32,address,address,uint256,uint256,uint256,uint256,uint256)",
}


def topic(sig):
    return "0x" + keccak256(sig.encode()).hex()


def code_len(addr):
    code = rpc("eth_getCode", [addr, "latest"], fresh=True)
    return (len(code) - 2) // 2


def main():
    out = {"topics": {k: topic(v) for k, v in SIGS.items()}}
    dec = rpc("eth_call", [{"to": PUSD, "data": "0x313ce567"}, "latest"], fresh=True)
    out["pusd_decimals"] = int(dec, 16)
    head = int(rpc("eth_blockNumber", [], fresh=True), 16)
    out["head_block"] = head
    out["code_bytes"] = {k: code_len(v) for k, v in {**ADAPTERS, "exchangeV3": EXCHANGE_V3,
                                                      **EXCHANGES}.items()}
    out["live_logs"] = {}
    for name, addr in EXCHANGES.items():
        logs = rpc("eth_getLogs", [{"fromBlock": hex(head - 300), "toBlock": hex(head - 100),
                                    "address": addr}], fresh=False)
        counts = {}
        for lg in logs:
            counts[lg["topics"][0]] = counts.get(lg["topics"][0], 0) + 1
        out["live_logs"][name] = {"n": len(logs), "by_topic0": counts,
                                  "sample_tx": logs[0]["transactionHash"] if logs else None}
    with open(os.path.join(os.path.dirname(__file__), "..", "data", "contract_checks.json"), "w") as f:
        json.dump(out, f, indent=1)
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
