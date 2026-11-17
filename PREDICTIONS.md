# PREDICTIONS: definitions, sample rule, predictions, kill condition

Written 2026-11-17 before any market, API or chain data was pulled. This file is not edited after Gate 1 is passed. Changes after that go in `DEVIATIONS.md` with a date and a reason, and the original text here stays. Reading contract source and documentation (`DOCS_FIRST.md`) is the only thing done so far.

## 1. Scope and the question

Question. For Polymarket markets that resolved in October 2026, by how much does a count built from summing exchange fill events overstate traded size, compared with the collateral that actually moved in the transaction receipts?

Exchanges in scope: CTF Exchange V2 (standard) and NegRisk CTF Exchange V2 (neg-risk). Both emit the V2 `OrderFilled` and `OrdersMatched` events (DOCS_FIRST section 2). ExchangeV3 and PositionManager markets are out of scope (section 4, rule 3), because their event layout is not documented.

Unit. Everything is computed in pUSD, assuming 6 decimals (to verify), and in outcome shares. The market is the unit of analysis. Results are market-level aggregates only.

## 2. Definitions: counting methods

A match is one `matchOrders` call. In a receipt, a match is the run of logs from just after the previous `OrdersMatched` (or the start of the transaction) up to and including its own `OrdersMatched`. One transaction can hold several matches. Rows are the `OrderFilled` logs in that run. A row is a taker row if its `taker` field equals the exchange address, otherwise a maker row.

For a row `r`:
- `cash(r)` = `makerAmountFilled` if `side` is BUY, else `takerAmountFilled`.
- `shares(r)` = `takerAmountFilled` if `side` is BUY, else `makerAmountFilled`.
- `fee(r)` = the `fee` field.

Market totals are sums over all matches of the market.

| Code | Name | Definition |
|---|---|---|
| (a1) N1 | Naive cash | Sum of `cash(r)` over all rows, taker rows and maker rows. |
| (a2) N2 | Naive shares | Sum of `shares(r)` over all rows. |
| (a3) W | Wallet-attributed cash | A taker-field parser: each row is credited to its maker field, and again to its taker field when that is not the exchange. W = T + 2 Mk. This is the market-level analogue of the 49% wallet effect in the earlier repo. |
| (b1) OM | Documented cash | Sum over matches of the `OrdersMatched` cash (`makerAmountFilled` if side is BUY, else `takerAmountFilled`). This is the one-sided reading that Paradigm and Rocknblock describe as correct. |
| (b2) OMs | Documented notional | Sum over matches of the `OrdersMatched` shares. |
| (b3) T, Mk | One-sided parts | T = cash over taker rows. Mk = cash over maker rows. Check: T = OM exactly. N1 = T + Mk. |
| (c) C | Receipt cash | Gross collateral that crossed the trader boundary, each dollar counted once, from pUSD `Transfer` logs. Definition below. |
| (d) V | Venue volume | Gamma `volumeNum` for the market (primary) and `volumeClob` (secondary), read after the market closed. Where a market is fully enumerated, also the sum of `size × price` and the sum of `size` over the Data API v2 `/v2/trades` rows for the market. |

Receipt cash C. Let `A` be the set of maker-field addresses in the match. These are the traders. In the match window, for each address `a` in `A`, take net pUSD flow `d_a` = pUSD received minus pUSD sent, from all `Transfer` logs in the window that touch `a`. Wrap, unwrap, mint and burn legs touch the pUSD contract, adapters, Conditional Tokens and the zero address, not traders, so they drop out by construction. Refunds net out because they are received and sent by the same address. Then:

- `Pay` = sum of `-d_a` over traders with `d_a < 0`.
- `Recv` = sum of `d_a` over traders with `d_a > 0`.
- `F_buy` = sum of `fee(r)` over BUY rows. `F_sell` = sum of `fee(r)` over SELL rows.
- Primary `C = max(Pay - F_buy, Recv + F_sell)`, the collateral excluding fees.
- `C_incl = C + F_buy + F_sell`, reported as a sensitivity.

Why this works, from the contract source (DOCS_FIRST sections 2 and 6): in a complementary match buyers pay X and sellers receive X, so `Pay = Recv` up to fees. In a mint match buyers pay S and nobody receives. In a merge match sellers receive S and nobody pays. In a mixed match one of the two sides is larger and it is the one that holds every dollar once. Matches where one address is both a maker-field trader and on both sides (a self-trade) are counted and reported separately.

One-sided versus two-sided, stated explicitly. N1 is, by arithmetic, the two-sided cash flow: every dollar counted once at the buyer and once at the seller where both exist. In a complementary match it is 2X. In a mint or merge match there is only one end, so it is about S. I predict that N1 equals `Pay + Recv` within 1% on the median market (prediction P12). So "overstates" in this study means "counts a dollar at both ends compared with counting each collateral dollar once". Someone may legitimately want two-sided volume. The point of the study is the size of the gap between the two conventions and which one the venue reports.

Ratios reported. Each of N1, N2/OMs, W, OM, Mk, T and V divided by C (and N2 divided by OMs for shares). For each ratio: median across markets, 25th and 75th percentile, minimum and maximum. The kill statistic and the primary table use market-level sums, not match-level ratios.

## 3. What the documentation predicts (formulas the data should satisfy)

From DOCS_FIRST section 6, with `f` the share of C moving in complementary matches (or the complementary part of mixed matches):

- N1 / C = 1 + f, plus a small positive term from taker rows that report the offered amount instead of the amount spent.
- N2 / OMs = 2 in every match type.
- OM / C and Mk / C are each about `0.5 + 0.5 f` if the taker side holds half of S on average.
- W / C = (T + 2 Mk) / C, about three times `0.5 + 0.5 f`.

## 4. Fixed sample rule

Fixed now. Not changed after data is seen. Deviations only through `DEVIATIONS.md`.

Frame. All Gamma markets, built once from the Gamma API (metadata only, no trades), then hashed and stored as `data/frame.json` with its SHA-256 before any fill is read. A market is in the frame if all of these hold:

1. `closed` is true and `closedTime` is on or after 2026-10-01T00:00:00Z and before 2026-11-01T00:00:00Z.
2. `startDate` is on or after 2026-09-01T00:00:00Z. This keeps each market's whole life within about two months, so its fills can be enumerated end to end. It excludes long-dated markets. This is a limitation and will be in the article.
3. Gamma `version` is `"v1"` (CTF position system, so fills are on CTF Exchange V2 or NegRisk CTF Exchange V2). Markets with `version` `"v2"` (ExchangeV3) are counted and reported as excluded. They are not sampled, because their `OrderFilled` layout is undocumented in the sources read.
4. `volumeNum` is at least 1,000 USD when the frame is built.

Cells. Six cells: exchange type (standard or neg-risk, from the event's `negRisk` flag, cross-checked against the exchange address of the market's first fill, with disagreements reported) times a volume band from `volumeNum` at frame build:

- small: 1,000 to under 25,000 USD
- medium: 25,000 to under 500,000 USD
- large: 500,000 USD or more

Draw. In each cell, sort eligible markets by `sha256(conditionId + "|fill-counting-2026")` as lowercase hex, ascending. Walk the list and take a market unless two markets of the same Gamma event were already taken. Stop at 10 per cell. No random number generator is used. A cell with fewer than 10 eligible markets contributes all of them, with no backfill from other cells. The target is 60 markets.

Pilot. The first 3 drawn in each cell (18 markets) plus the 4th drawn in each large cell (2 markets), 20 in total. A short cell gives a shorter pilot, with no substitution. The kill condition (section 7) applies to the pilot.

Receipt budget. Fills of a market are enumerated from its start to its `closedTime`. A market with at most 1,000 fill transactions is read in full. A larger market is read as a deterministic subsample: keep transactions whose hash, as an integer, is divisible by `2^k`, where `k` is the smallest integer that expects at most 1,000 kept transactions. The ratios in section 2 are scale free, so a subsample estimates them. Subsampled markets are flagged, and are left out of any comparison with venue volume (d) that needs a total. If the frame cannot be enumerated within the shared-RPC rules, the budget is cut by lowering 1,000 uniformly for all markets and logged in `DEVIATIONS.md`.

Stop rules. If the frame has fewer than 30 eligible markets in total, stop and report before pulling any fills. If it has 30 to 59, proceed with all of them and say so.

## 5. Predictions

Each prediction is about a statistic over the full sample unless it says "pilot". A hit is an observed value inside the stated range. A miss is reported with the size of the gap. Ranges are my 80% intervals.

Identity checks (should be exact or near exact):

| # | Prediction | Range |
|---|---|---|
| P1 | T equals OM on every match. | 100% of matches, difference 0 |
| P2 | In pure complementary matches, the sum of maker-row cash equals the taker-row cash. | 100% of matches, within 1 base unit |
| P3 | N2 / OMs, median across markets. | 1.98 to 2.02 |
| P4 | In pure mint and merge matches, the sum of row cash divided by C, median over matches. | 1.000 to 1.010 |
| P12 | `abs(N1 - (Pay + Recv)) / N1`, median across markets. | 0 to 0.01 |

Composition:

| # | Prediction | Range |
|---|---|---|
| P5 | f, the complementary share of C, median across markets. | 0.40 to 0.85, point 0.65 |
| P6 | Share of matches that are mint or merge or mixed with either, by count. | 15% to 55%, point 30% |
| P7 | Share of matches that are mixed (complementary plus mint or merge). | 5% to 35%, point 15% |

Headline ratios to receipts, median across markets (the table in the article):

| # | Ratio | Range | Point |
|---|---|---|---|
| P8 | N1 / C | 1.40 to 1.85 | 1.65 |
| P9 | OM / C | 0.70 to 0.95 | 0.83 |
| P10 | Mk / C | 0.70 to 0.95 | 0.83 |
| P11 | W / C | 2.10 to 2.80 | 2.5 |

Spread (across markets, for N1 / C): 25th percentile 1.30 to 1.60, 75th percentile 1.70 to 1.95, minimum at least 1.05, maximum at most 2.10. Taker side and maker side agree: median of `abs(OM/C - Mk/C)` across markets is at most 0.10 (P13).

Venue volume:

| # | Prediction | Range or probability |
|---|---|---|
| P14 | Gamma `volumeNum` / OM, median across fully enumerated markets. | 0.95 to 1.05 |
| P15 | What the venue's market volume is. | One-sided taker cash 60%, collateral C 20%, two-sided N1 5%, shares or something else 15% |

P14 holds only if the venue reports one-sided taker cash. If the venue reports two-sided cash, `volumeNum / N1` will be in 0.95 to 1.05 instead and P14 misses. This is the one place where the documentation is silent, so it is the prediction I trust least.

Other:

| # | Prediction | Range |
|---|---|---|
| P16 | Total row fees divided by C, median across markets. | 0 to 1.5%, point 0.2% |
| P17 | Share of sampled markets with zero fees in every row. | 25% to 80% |
| P18 | N1 / C for neg-risk markets minus the same for standard markets, absolute difference of medians. | 0 to 0.15 |
| P19 | The wallet-level effect does not net out at market level: the market-level wallet-attribution overstatement (W / C minus 1) exceeds the earlier 49%. | W / C minus 1 between 1.10 and 1.80 |
| P20 | Matches in which the maker field address is also the taker order's maker (self-trades), share of matches. | 0% to 2% |

Frame and feasibility (recorded, scored loosely):

| # | Prediction | Range |
|---|---|---|
| P21 | Every one of the six cells has at least 10 eligible markets in the frame. | Large cells are the likeliest to fall short. I give 60% that all six cells fill to 10. |
| P22 | Share of frame candidates (rules 1, 2, 4 met) excluded because `version` is `"v2"`. | No informed prior. I record it. If it is above 50%, the article will say the study speaks for the CTF-position markets only. |

Net-out expectation. The brief says the wallet effect may net out. My expectation is that it does not, for a stated reason: complementary matches repeat the same cash in the taker row and in the maker rows, and nothing on the other side cancels it. Mint and merge matches do not repeat cash, which pulls the cash ratio from 2.0 down to `1 + f`, but not to 1.

## 6. Scoring

After the full run, each prediction is scored hit, near miss (outside the range by less than 20% of the range width) or miss, with the observed value. The probabilities in P15 and P21 are scored by outcome. Misses are reported in the article and in the post pack. No prediction is rewritten.

## 7. Kill condition

Statistic. Over the 20 pilot markets, the median of `N1 / C - 1`, each market's N1 and C being market-level sums over its enumerated fills (subsampled markets use the subsample), in pUSD, C excluding fees.

Rule. If that median is below 0.05, the study stops. The result is a one-page note saying the wallet-level effect does not carry to market level. If it is 0.05 or above, the study continues to the full sample.

Notes. The kill uses cash only. The share-based result (P3, always about 2) is reported but cannot override a cash result either way. The kill is checked once, on the pilot, before the other 40 markets are read. My expectation is a pilot median of 0.40 to 0.85, so I give about 3% that the study is killed.

## 8. What could make the finding wrong, and where it is handled

- Two-sided versus one-sided by definition: section 2 states N1 is two-sided accounting, P12 tests it, and the table gives both readings.
- Mint and merge legs that move collateral without a trade: C counts the collateral S once, so a mint or merge match carries weight in C. A separate column splits C into complementary, mint and merge shares (P5 to P7).
- Neg-risk conversions: `convertPositions` is outside `matchOrders` (DOCS_FIRST section 2 point 7). Matches are windowed by `OrdersMatched`, so a conversion in the same transaction falls outside the window. Self-trades and any window with unrelated transfers touching a trader are flagged.
- Fees: C excludes fees, `C_incl` includes them, P16 and P17 size them.
- Taker rows report offered cash in mint and merge matches: P4 measures the gap.
- Subsampling large markets: flagged, excluded from venue comparisons, and limited to ratios.
- Frame limits: markets that started on or after 2026-09-01 and closed in October, CTF position system only. Not all of Polymarket.
- The deployed contract may differ from the source read: checked by decoding one transaction per exchange before the pilot, logged in `DEVIATIONS.md` if it differs.

## 9. Order of work after Gate 1 is passed

1. Check pUSD decimals and the V2 `OrderFilled` topic0 against one known transaction per exchange.
2. Build `data/frame.json` from the Gamma API, hash it, draw the sample, write `data/sample.json`.
3. Pilot: 20 markets, then the kill check.
4. Full 60 markets, then one script recomputes every number from files in the repo.
