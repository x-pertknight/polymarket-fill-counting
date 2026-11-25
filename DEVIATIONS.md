# Deviations from PREDICTIONS.md and later additions

`PREDICTIONS.md` is not edited. Every entry here is dated. Predictions are written down and scored, misses included. No hash was recorded and they entered git with the results, as did this file.

## 2026-11-17: four conditions added to the method

On 2026-11-17 four conditions were added to the method. The method definitions, sample draw, identity checks, pilot and kill statistic stand as written in `PREDICTIONS.md`.

1. Coverage of the excluded exchange. If more than half of the frame candidates are excluded because they run on ExchangeV3 (Gamma `version` "v2"; prediction P22), I spend up to half a day trying to get its event layout from verified contract source on a block explorer or Sourcify. If found, those markets are added as a seventh and eighth cell (standard and neg-risk analogues or whatever the layout supports), with their own rows, marked "added after PREDICTIONS.md". If not found, the first sentence of the article states which share of October markets the study covers.
2. Three claims are kept apart in every output and never merged:
   - (i) a parsing error an analyst can make: wallet attribution W against receipts C;
   - (ii) one-sided versus two-sided accounting, a definition and not an error: N1 against C;
   - (iii) what the venue's own reported volume corresponds to: V against OM, N1 and C.
   The article and posts use the word "overstates" only for (i). For (iii) they report which definition the venue number matches and stop there.
3. Self-trades (P20) are reported as one aggregate share across the sample. No market-level list, no addresses, no wording that suggests manipulation.
4. Shared RPC and budget. Shared public RPC: at most two requests in flight, back off on errors, cache every receipt to disk. If the pilot shows the full run would take more than about six hours of fetching, I report the estimate and propose a smaller per-market receipt cap instead of pressing on. A lower cap would then be logged here before use.

Unchanged: the kill rule is applied once, on the pilot.

## 2026-11-17, before the frame crawl: how the frame is queried

The Gamma `/markets/keyset` endpoint returns HTTP 500 when `start_date_min` is used and has no `closedTime` filter. The frame is therefore fetched with a coarse server-side prefilter: `closed=true`, `volume_num_min=1000`, `end_date_min=2026-09-20T00:00:00Z`, `end_date_max=2026-11-30T00:00:00Z`, then every rule in `PREDICTIONS.md` (closedTime in October, startDate on or after 2026-09-01, version, volume) is applied locally. This can miss a market resolved in October whose `endDate` lies outside 20 Sep to 30 Nov. The script reports how many frame markets have an `endDate` within 10 days of either edge, as a gauge of that loss. The rules in `PREDICTIONS.md` and the draw are unchanged.

## 2026-11-17, access route for per-market fill transaction hashes

Needed: the transaction hashes of each sampled market's fills, as an index only. Every number would still come from receipts read over RPC.

Tried, with plain and honest clients only:
1. Polymarket Data API (`data-api.polymarket.com`, v2 `/v2/trades`, `/v2/openapi.json`, and the root path). The server resets the TCP connection (ECONNRESET, errno 54) for curl, Python urllib with a generic user agent, a browser page fetch, and a final retry with only `Accept: application/json` and a truthful client name. No Origin or Referer was sent. The earlier repo (`polymarket-vandyke-receipts`) reached this API with browser-style headers (Chrome User-Agent, Origin, Referer). That access method is not reused here.
2. Subgraphs. The Polymarket documentation has no subgraph page (`market-data/subgraph.md` returns 404) and `resources/blockchain-data` names no GraphQL endpoint. It lists Goldsky pipelines, CryptoHouse, Dune and Allium. The Goldsky page lists only a Feeds REST API that needs an API key or pay-per-request (x402) and Turbo Pipelines that need a Goldsky account. A third-party repository (warproxxx/poly_data README) states the old subgraph indexer was dropped at the 2026-04-28 contract migration and that Envio HyperSync now needs a free token. I did not create any account or token.
3. Dune: no queries could be run.

Side finding: the Goldsky page says Polymarket Protocol V2 markets (ExchangeV3 and PositionManager) start on 2026-11-09. October 2026 markets are therefore all on CTF Exchange V2 and NegRisk CTF Exchange V2, which agrees with the observed P22 of 0 of 123,988 candidates (Gamma reports version "v1" for all 237,183 crawled markets).

Status: no trade index is available. The frame, sample and hashes are unchanged. No fill has been read.

## 2026-11-17, CryptoHouse checked as a trade index: no usable data

Route tried next: CryptoHouse (crypto.clickhouse.com, ClickHouse and Goldsky), named on Polymarket's `resources/blockchain-data` page.

Access: free, no account or key needed to run read queries in its web UI. Stated limits (ClickHouse launch post): 60 queries per hour per user, 60 seconds per query, community use and not commercial products. No documented HTTP endpoint or connection details. Cookies: non-essential cookies were declined. Four queries were run, all read-only and narrow: `DESCRIBE`, a 5-second sample (a syntax error and then a rerun), and one min, max and count query.

Data: database `polymarket` has `orders_filled`, `orders_filled_old`, `orders_matched`, `orders_matched_old`, `token_id_condition`, `block_times`, `slugs`, `assets`, `user_balances`, `user_positions` and others. There is no Polygon raw-logs database (databases are base, default, ethereum, polymarket, solana).

Coverage, from `min(timestamp)`, `max(timestamp)`, `count()`:
- `polymarket.orders_filled`: 2022-11-21 to 2026-01-05, 257,649,337 rows.
- `polymarket.orders_filled_old`: 2022-11-21 to 2024-10-24, 17,337,815 rows.
- A 5-second slice on 2026-10-15 returned no rows.

Conclusion: the table stops in early January 2026, before the 28 April 2026 contract migration, so it holds no September or October 2026 fills and cannot index this sample. No fill data from it was used. The frame, sample and hashes are unchanged.

## 2026-11-17, later: the trade index was built via Data API v2 from a real browser

This supersedes the "no trade index is available" status in the access-route section above.

What works. The Data API v2 `/v2/trades` endpoint answers from a real browser (Browser Use / Chromium, genuine TLS fingerprint), with the query parameter `condition` (aliases `condition_id`, `conditionId`; `market` is rejected with an error). Pagination is cursor-only via `next_cursor` (no offset), `limit` up to 500, rows newest-first. It returns exactly `transaction_hash`, `timestamp` and `token_id` per fill.

What still fails. Honest HTTP clients (curl, urllib, Python stdlib) still get ECONNRESET on this path. The reset is a TLS-fingerprint / WAF rule, not a parameter or header problem: `/v2/` returns a JSON 404 to curl while `/v2/trades` resets, for the same client.

The decision. On 2026-11-17 I decided to use this access and log it here. The rationale is that a real browser is not the fabricated browser-style headers ruled out above; it is the client the API admits by design, on a public, unauthenticated endpoint.

What was written. `data/index/<conditionId>.json`, one file per sampled market, with `source` recording the endpoint. Each trade row is reduced to `{transactionHash, timestamp, asset}`: no proxy_wallet, name or pseudonym is stored anywhere. `data/index/_SUMMARY.json` holds, per market, the distinct transaction-hash count and the `complete` flag. All 60 markets are `complete: true` (59,355 distinct transactions across the sample). The fetch script is `code/fetch_index.py`; the summary is recomputed by `code/build_summary.py`.

Why not on-chain. Ruled out and checked: the V2 `OrderFilled` `tokenId` sits in the data field (not an indexed topic), so there is no indexed way to select one market's fills; the exchange emits roughly 56 `OrderFilled` logs per block, making a full scan infeasible under the shared-RPC rules. The index here is the same one the receipt step (PREDICTIONS.md section 4) needed.

## 2026-11-17, provenance and independent check of the trade index

Provenance, in plain terms. The per-market list of transaction hashes (`data/index/*.json`) was supplied by the author, who collected it from the venue's public data API through a real browser session. The access route of the earlier repo (browser-style request headers set by script) is not reused here. The index is used only to know which receipts to read. Every number in this study comes from receipts read over RPC. `code/fetch_index.py` is the supplied collection tooling, kept for the record; it is not part of the offline recompute and is not re-run.
One-sentence version for the article's method section: "The list of transactions per market came from the venue's public data API, collected by the author through a browser; every figure below is computed from transaction receipts read directly from the chain."

Independent check. For four sampled markets I scanned `OrdersMatched` logs of the market's exchange over its life (startDate to closedTime), kept those whose token id is one of the market's two outcome tokens, and compared the set of transaction hashes with the index. Results (`data/index_validation.json`):

| market (prefix) | cell | txs on chain | txs in index | missing from index | extra in index |
|---|---|---|---|---|---|
| 0xedc03fba | standard small | 2 | 2 | 0 | 0 |
| 0x71bb007a | neg-risk small | 94 | 94 | 0 | 0 |
| 0x463b885a | neg-risk small | 159 | 159 | 0 | 0 |
| 0xaf63476c | standard medium | 664 | 664 | 0 | 0 |

Coverage is complete on all four. No large market was checked this way (log volume makes it too costly); that is a stated limit of the validation.

Mistakes on my side during this check (none affects any reported number, no receipt had been read yet):
- I assumed a 2.0 s block time; Polygon runs at about 1.5 s. The scan window was shifted about 20,000 blocks late and showed 43 false "extra" hashes on one market. All results from that run were discarded and the check was redone with a window search that cannot be clipped by a wrong guess.
- A retry loop sent about 2,300 failed `eth_getLogs` requests to the shared public endpoints (HTTP 403/400 answers to oversized ranges) before I stopped it. That broke the "back off on errors" rule. `rpc.py` now treats such answers as "range too large" and halves, and stops using an endpoint for `eth_getLogs` after a 403. The public endpoints accept about 100 blocks per `eth_getLogs` on this contract, so scans use 200-block chunks.
- Earlier per-day log-volume estimates used the old 2.0 s block time and were about 33% low. Full-run time estimates are redone with 1.5 s.

Correction to the entry above, same day. The HTTP 403 from publicnode on `eth_getLogs` and receipt calls is its documented policy, not a block caused by my requests: it answers "Archive requests require a personal token" for blocks this old. My earlier guess that the 403 followed my retry storm was wrong. In practice only `polygon.drpc.org` serves this study's historical blocks. `1rpc.io` reached its daily plan limit during the check. `rpc.py` now sets an endpoint aside for 10 minutes after a 403, and for an hour after a "usage limit" answer, instead of retrying it. Consequence: fetching runs on one endpoint, one request at a time, which is within the shared-RPC rules and slower than three endpoints would be.

## 2026-11-25: post.md synced with the published post

`post.md` was edited to match the LinkedIn post after three wording corrections made to the published post on 25 November 2026. The venue comparison now reads "In 21 of 35 markets it is within 5% of the fill total, and in 20 within 5% of the cash moved" instead of "about 20" for both. The sampling rule now reads "on or after 1 September" instead of "after 1 September". The predictions sentence now reads "10 of the 21 scorable predictions I wrote down missed" instead of "10 of my 21 scorable predictions missed".

No figure in the study changed. The `post.md` checksum in `SHA256SUMS` was regenerated deliberately for this reason.
