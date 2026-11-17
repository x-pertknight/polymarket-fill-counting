# Polymarket fill counting: how much does summing fill events differ from cash that moved?

Technical document for the post (`post.md`, image `charts/summary.png`). Study 6. Read-only research on public chain data; no trading, no accounts.

## Question and the three claims (kept apart)

For 60 Polymarket markets that closed in October 2026, compare counts built from exchange fill events with the collateral (pUSD) that actually crossed trader wallets in the transaction receipts.

1. **Parsing error (W against C).** A parser that credits each fill to its `maker` field and again to its `taker` field counts the same cash twice. This is an error a parser can make. Only this claim uses the word "overstates".
2. **One-sided against two-sided accounting (N1 against C).** Summing every `OrderFilled` row counts a dollar at both ends where both ends exist. That is a definition, not an error.
3. **What the venue's reported volume corresponds to (V against N1, OM, C).** Reported as a match to a definition, with the number of markets it rests on.

## Result in one table (60 markets, median across markets; 25th to 75th percentile; min to max)

| ratio to receipt cash C | median | p25 to p75 | min to max | claim |
|---|---|---|---|---|
| W / C (wallet attribution) | 1.678 | 1.588 to 1.802 | 1.123 to 2.025 | (i) |
| N1 / C (every fill row, both ends) | 1.105 | 1.045 to 1.164 | 1.000 to 1.448 | (ii) |
| OM / C (`OrdersMatched` cash, taker side) | 0.567 | 0.502 to 0.632 | 0.002 to 0.978 | (ii) |
| Mk / C (maker-row cash) | 0.559 | 0.514 to 0.610 | 0.098 to 0.998 | (ii) |
| N2 / OMs (shares) | 2.000 | 2.000 to 2.000 | 2.000 to 2.000 | identity |

Match composition, 23,967 matches: pure mint or merge 71.4%, pure complementary (buyer meets seller) 20.1%, mixed 8.5%. The complementary share of collateral (f) has median 0.105. This is why N1/C is near 1.1: in a mint or merge match the row cash adds up to the collateral once.

## Venue volume (claim iii): 35 fully enumerated markets

V is Gamma `volumeNum`, read after close (`volumeClob` equals it in all 60 markets). Only markets read in full (no subsampling) are used.

| ratio | median | p25 to p75 | min to max | markets within 5% of 1 |
|---|---|---|---|---|
| V / N1 | 0.992 | 0.941 to 1.001 | 0.693 to 1.317 | 21 of 35 |
| V / C | 1.042 | 1.004 to 1.102 | 1.000 to 1.531 | 20 of 35 |
| V / OM | 1.902 | 1.674 to 2.769 | 1.023 to 488.6 | 1 of 35 |
| V / Mk | 1.953 | 1.740 to 2.187 | 1.002 to 12.04 | 2 of 35 |

Statement supported: the venue's figure (volume as Polymarket reports it after close) is within 5% of N1 in 21 of 35 markets and of C in 20, and far from OM. Where N1 and C differ it sits between them; the data cannot tell which one it tracks. Split by how far N1 and C differ: where f is below 0.05 (14 markets) N1 and C are about equal and V matches both (V/N1 1.00, V/C 1.02); where f is 0.15 or more (9 markets, N1/C 1.23) V is 9% below N1 (0.91) and 10% above C (1.10). The sample is mostly small and medium markets: fully enumerated markets by cell are 10, 6, 2 (standard small, medium, large) and 10, 7, 0 (neg-risk). The study does not show how the venue computes its figure.

## By cell (medians; V ratios on fully enumerated markets, count in brackets)

| cell (markets) | N1/C | OM/C | W/C | V/N1 | V/C | V/OM |
|---|---|---|---|---|---|---|
| standard (30) | 1.093 | 0.543 | 1.667 | 0.992 (18) | 1.035 | 1.972 |
| neg-risk (30) | 1.121 | 0.596 | 1.685 | 0.993 (17) | 1.045 | 1.716 |
| small (20) | 1.069 | 0.555 | 1.669 | 0.993 (20) | 1.044 | 1.923 |
| medium (20) | 1.102 | 0.558 | 1.678 | 0.976 (13) | 1.040 | 1.888 |
| large (20) | 1.132 | 0.578 | 1.725 | 0.987 (2) | 1.038 | 2.143 |
| standard small (10) | 1.082 | 0.529 | 1.663 | 0.992 (10) | 1.028 | 1.972 |
| standard medium (10) | 1.110 | 0.548 | 1.711 | 0.983 (6) | 1.064 | 1.955 |
| standard large (10) | 1.078 | 0.547 | 1.652 | 0.987 (2) | 1.038 | 2.143 |
| neg-risk small (10) | 1.056 | 0.607 | 1.716 | 1.001 (10) | 1.051 | 1.768 |
| neg-risk medium (10) | 1.098 | 0.581 | 1.667 | 0.976 (7) | 1.040 | 1.681 |
| neg-risk large (10) | 1.154 | 0.601 | 1.781 | none | none | none |

Full ranges per cell are in `data/results_all.json` (`groups`).

## Subsampling

A market with more than 1,000 fill transactions is read as a deterministic subsample (transaction hash divisible by 2^k, k the smallest value that expects at most 1,000 kept). 25 of 60 markets are subsampled, including most large ones. Subsampled markets: N1/C median 1.126; fully enumerated: 1.068. That difference is mostly market size, because the two groups differ in volume. A direct test: on the 9 fully enumerated markets with at least 300 transactions, re-drawing the same hash rule at k = 1 and k = 2 moved N1/C by a median of -0.027 and -0.051 (always downward, absolute median 0.035 and 0.054). So subsampling does not inflate the headline; if anything it understates it slightly. Based on 9 markets only. Subsampled markets are left out of every venue comparison.

## Pre-registered predictions: 11 hits, 10 misses of 21 scorable (P22 had no prior and is recorded only)

Scored against `PREDICTIONS.md` (not edited). P22 had no prior, so 21 are scorable. No near misses. The misses are mostly one error: I predicted most collateral moves in buyer-meets-seller matches. It does not; most matches are mint or merge.

| # | prediction | observed | result |
|---|---|---|---|
| P1 | T equals OM on every match | 23,967 of 23,967 | hit |
| P2 | pure complementary: maker-row cash equals taker cash | 4,812 of 4,812 | hit |
| P3 | N2/OMs 1.98 to 2.02 | 2.000 on every market | hit |
| P4 | mint/merge row cash over C, 1.000 to 1.010 | 1.000 (all 60 market medians) | hit |
| P5 | f 0.40 to 0.85 | 0.105 | miss |
| P6 | mint, merge or mixed share 15 to 55% | 79.9% | miss |
| P7 | mixed share 5 to 35% | 8.5% | hit |
| P8 | N1/C 1.40 to 1.85; p25 1.30 to 1.60; p75 1.70 to 1.95; min at least 1.05; max at most 2.10 | 1.105; 1.045; 1.164; 1.000; 1.448 | miss (only the max holds) |
| P9 | OM/C 0.70 to 0.95 | 0.567 | miss |
| P10 | Mk/C 0.70 to 0.95 | 0.559 | miss |
| P11 | W/C 2.10 to 2.80 | 1.678 | miss |
| P12 | abs(N1 - (Pay + Recv)) / N1 median 0 to 1% | 0.4% | hit |
| P13 | median abs(OM/C - Mk/C) at most 0.10 | 0.099 | hit (barely) |
| P14 | V/OM 0.95 to 1.05 | 1.902 | miss |
| P15 | venue = taker cash 60%, C 20%, N1 5%, other 15% | within 5% of OM in 1 of 35; of N1 in 21; of C in 20 | miss on the 60% call |
| P16 | fees/C 0 to 1.5% | 0.6% | hit |
| P17 | 25 to 80% of markets with zero fees | 0 of 60 | miss |
| P18 | N1/C neg-risk minus standard, 0 to 0.15 | 0.028 | hit |
| P19 | W/C minus 1 between 1.10 and 1.80 | 0.678 (it does exceed the earlier repo's 49%) | miss |
| P20 | self-trade share 0 to 2% | 0 of 23,967 (0%) | hit |
| P21 | every cell has at least 10 eligible markets | smallest cell has 219 | hit |
| P22 | share of candidates excluded as ExchangeV3 | 0 of 123,988 | recorded, below 50% |

Kill rule (pilot, applied once): median of N1/C minus 1 over the 20 pilot markets was 0.097, above the 0.05 threshold, so the study continued.

## Other checks that held

- 100% of 23,967 matches: taker-row cash equals the `OrdersMatched` cash.
- Fees are 0.6% of C at the median (max 1.9%); all 60 markets charge fees.
- Self-trades (maker-field wallet equals the taker order's maker): 0 matches of 23,967. Reported only as this one aggregate.

## Method (short; full definitions in `PREDICTIONS.md`, contract reading in `DOCS_FIRST.md`)

- Exchanges: CTF Exchange V2 and NegRisk CTF Exchange V2 (live since 28 Apr 2026; collateral pUSD, 6 decimals). A match is one `matchOrders` call: the run of logs ending in its `OrdersMatched` event. Rows are its `OrderFilled` logs.
- N1 is the sum of row cash over taker and maker rows. W = T + 2 Mk. OM is the `OrdersMatched` cash. C is the collateral that crossed trader wallets once, from net pUSD flow per maker-field wallet in the match window: `C = max(Pay - F_buy, Recv + F_sell)`, fees excluded.
- Frame: Gamma markets that closed in October 2026, started on or after 1 September, volume of at least 1,000 USD, CTF position system. Six cells (standard or neg-risk by three volume bands), 10 per cell, hash-ordered with no random generator. 20 of the 60 form the pilot.
- Which transactions to read: the transaction list per market (`data/index/`) came from the venue's public data API, collected by the author through a browser; every figure is computed from transaction receipts read directly from the chain. The list was checked against a direct chain scan on four markets (2, 94, 159 and 664 transactions): zero missing and zero extra transactions. No large market was checked this way.
- Receipts: read over public RPC, one request at a time, cached. Each receipt is reduced to the logs of the two exchanges and the pUSD contract (`code/fetch_receipts.py`).

## Limits

- Frame: markets that started on or after 1 September 2026 and closed in October 2026, CTF position system only (all October markets; ExchangeV3 launched 9 November). Not all of Polymarket.
- 25 of 60 markets are subsampled, most large ones; venue comparison has 2 large markets and none in the neg-risk large cell.
- C assumes the maker-field address holds the cash. A proxy or custody setup could hide flows; the 0.4% agreement of N1 with Pay + Recv at the median is a consistency check, not proof.
- Matches are windowed by `OrdersMatched`. Neg-risk conversions sit outside `matchOrders` and are not counted.
- The index validation covers four small and medium markets.
- The venue comparison shows which definitions the venue figure is near, not how it is built.

Deviations from the pre-registration, and the mistakes made along the way (a wrong block-time assumption in the validation scan, a retry loop on the shared endpoints), are logged in `DEVIATIONS.md`.

## Reproduce (offline, from saved files, standard library only)

```
python3 -I code/compute.py all     # data/results_all.json
python3 -I code/score.py           # data/scoring.json
python3 -I code/charts.py          # charts/summary.png (needs Chrome)
shasum -a 256 -c SHA256SUMS
```

`code/fetch_index.py`, `code/fetch_receipts.py`, `code/validate_index.py` and the frame scripts need the network and are not part of the recompute. The raw RPC cache (`data/cache/`, about 6 GB) is not in the repo. The market frame files (`data/frame_raw.jsonl`, 806 MB, and `data/frame.json`, 72 MB) are also left out because of GitHub's file size limit; the frame scripts rebuild them from the venue's public market list, and their checksums are in `SHA256SUMS`. `code/score.py` needs them only for the frame counts (P21, P22); `code/compute.py` does not.

## Files

`DOCS_FIRST.md` contracts and events as documented; `PREDICTIONS.md` pre-registration (frozen); `DEVIATIONS.md` dated changes; `data/` frame, sample, index, reduced receipts, results; `code/`; `charts/summary.png`; `post.md`, `post_comment.md`.
