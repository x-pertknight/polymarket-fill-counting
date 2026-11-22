# DOCS_FIRST: what the documentation and contract source say, and what must be measured

Dated 2026-11-17. It entered git with the results (d441594). Nothing in this file comes from a data pull. Contract source was read directly from the public GitHub repositories (commits and file hashes in section 8). Documentation pages were read through a page fetcher that summarises, so each documentation claim below should be re-checked against the page itself before publication. Where a page is silent, that is stated.

## 0. The first finding: the contracts changed after the earlier repo

The earlier repo (`polymarket-vandyke-receipts`) analysed Dec 2025 to Jan 2026 trades on the original CTF Exchange, paid in USDC.e. October 2026 trades are on a different contract generation.

| Item | Earlier repo (V1) | October 2026 | Source |
|---|---|---|---|
| Standard exchange | CTF Exchange (V1) | CTF Exchange V2 `0xE111180000d2663C0091e4f400237545B87B996B` | contracts page; ctf-exchange-v2 README |
| Neg-risk exchange | NegRisk CTF Exchange (V1) | NegRisk CTF Exchange V2 `0xe2222d279d744050d28e00520010520000310F59` | same |
| Collateral | USDC.e | pUSD `0xC011a7E12a19f7B1f670d46F03B03f3342E82DFB` (the V2 README calls it PMCT) | same; changelog 17 Apr 2026 |
| Cutover | none | 28 Apr 2026, about 11:00 UTC | changelog |
| `OrderFilled` | `makerAssetId`, `takerAssetId`, 8 fields | `side`, `tokenId`, `builder`, `metadata`, 10 fields | ITrading.sol (V2) |
| Mint and merge | one CTF call per maker order | one batched CTF call per match | V2 README, `_settleMakerOrders` |
| Fees | per-order `feeRateBps` | set at match time, passed as `takerFeeAmount` and `makerFeeAmounts` | V2 `matchOrders`; changelog |
| Third system | none | ExchangeV3 `0xe3333700cA9d93003F00f0F71f8515005F6c00Aa` with PositionManager, EIP-712 domain version "3" | contracts page; onchain-position-data page |

Consequence: the earlier repo's 49% figure and its maker-field rule were measured on V1. Whether the same rule holds on V2 is a thing to measure, not to assume. The V2 source suggests it does (section 2), but this study measures it instead of assuming it.

## 1. Documented: what the original exchange (V1) emits

Source: `Polymarket/ctf-exchange` `src/exchange/mixins/Trading.sol` (SHA-256 in section 8), and the earlier repo's `NOTE-orderfilled-attribution.md`.

- One `matchOrders` call has one taker order and one or more maker orders.
- Each maker order emits one `OrderFilled(orderHash, maker, taker = takerOrder.maker, makerAssetId, takerAssetId, making, taking, fee)`.
- The taker order emits one more `OrderFilled` with `taker = address(this)`, the exchange, then one `OrdersMatched` (Trading.sol lines 166 to 170).
- `makerAssetId == 0` means the order maker is paying collateral (a buy). Otherwise the maker is paying outcome tokens (a sell).
- `_deriveMatchType`: taker BUY with maker BUY is MINT. Taker SELL with maker SELL is MERGE. Otherwise COMPLEMENTARY (lines 275 to 279).

## 2. Documented: what the current exchange (V2) emits

Source: `Polymarket/ctf-exchange-v2` `src/exchange/mixins/Trading.sol`, `Events.sol`, `interfaces/ITrading.sol`.

Event definitions (ITrading.sol lines 18 to 40):

```
OrderFilled(bytes32 indexed orderHash, address indexed maker, address indexed taker,
            uint8 side, uint256 tokenId, uint256 makerAmountFilled, uint256 takerAmountFilled,
            uint256 fee, bytes32 builder, bytes32 metadata)
OrdersMatched(bytes32 indexed takerOrderHash, address indexed takerOrderMaker,
              uint8 side, uint256 tokenId, uint256 makerAmountFilled, uint256 takerAmountFilled)
FeeCharged(address indexed receiver, uint256 amount)
```

Facts read from the code:

1. Rows per match. Every maker order emits one `OrderFilled` whose `taker` field is the taker order's maker (Trading.sol lines 240 to 253, 492 to 505, 523 to 536). The taker order emits one `OrderFilled` whose `taker` field is the exchange itself, immediately followed by `OrdersMatched` carrying the same four amount and side fields (`_emitTakerFilledEvents`, Events.sol lines 65 to 76). So the taker order is described twice (a row and a summary event), and the maker orders once each.
2. Row orientation. `side` is the order maker's own side. `tokenId` is the order's own token. In a mint or merge match the maker rows carry the complementary token, as in V1. For a BUY row, `makerAmountFilled` is collateral paid and `takerAmountFilled` is shares received. For a SELL row it is the reverse (Trading.sol lines 610 to 620: buy gives `makerAssetId = 0`).
3. Complementary matches (all makers on the opposite side of the taker). Settled peer to peer (`_settleComplementary`, lines 151 to 199). The taker row's `makerAmountFilled` and `takerAmountFilled` are sums of the maker rows' amounts (lines 168 to 178, 291 to 292). So in a pure complementary match the taker row repeats the maker rows' cash exactly.
4. Mint match (taker BUY, a maker BUY on the other outcome) and merge match (taker SELL, a maker SELL on the other outcome). Settled through the exchange with one batched CTF `splitPosition` or `mergePositions` per match (lines 426 to 428). The collateral that is split or merged equals `totalMintAmount` or `totalMergeAmount`, the sum of the makers' shares. A match can mix complementary makers with mint makers (taker BUY) or with merge makers (taker SELL), so mint and merge never occur together in one match (the same taker side cannot both mint and merge).
5. Taker row amounts in non-complementary matches. `takerAmountFilled` is the exchange's actual balance change (lines 122 to 125 and 328 to 330), not the sum of maker amounts, so it can exceed the minimum when the taker gets price improvement.
6. Fees. The `fee` field is the fee amount in collateral for that order. A taker BUY pays `takerFillAmount + takerFeeAmount` in (line 312). Maker and taker SELL fees are deducted from proceeds (lines 366 to 369, 513 to 517). `FeeCharged` is emitted per fee (Events.sol lines 78 to 86). The `fee` is not part of `makerAmountFilled` or `takerAmountFilled`.
7. Neg-risk exchange. `NegRiskCtfExchangeV2` uses the same `CTFExchange.sol` (V2 README, Deployed Contracts table). The mint and merge calls go to the `NegRiskCtfCollateralAdapter` instead of the standard adapter (adapter source). Neg-risk position conversion (`convertPositions`) is a separate user call on the adapter, not a `matchOrders` step, and emits no `OrderFilled`.
8. Collateral wrapping on mint and merge. The standard adapter pulls pUSD from the exchange, unwraps it to USDC.e, and calls the original Conditional Tokens contract (CtfCollateralAdapter lines 61 to 83). On merge it reverses this (lines 89 to 112). So a mint or merge receipt contains extra collateral transfers (wrap, unwrap, USDC.e) that are plumbing, not trader cash.

What the V2 source does not say:

- Whether the deployed bytecode equals the repository's `main`. The commit used is dated 2026-04-13, before the 28 Apr cutover. To verify at the build stage by comparing the `OrderFilled` topic0 and a decoded sample (no market data needed beyond one transaction).
- The decimals of pUSD. Assumed 6 like USDC.e, to verify with one `decimals()` call.

## 3. Documented: neg-risk adapter (V1 era, still the underlying)

Source: `Polymarket/neg-risk-ctf-adapter` `src/NegRiskAdapter.sol`. `splitPosition` and `mergePositions` move collateral in and out of the adapter. `convertPositions` releases collateral to the caller (and to the vault when a fee applies) and emits `PositionsConverted`. It is not a trade and is outside `matchOrders`.

## 4. Documented: what third parties say about counting

- Paradigm, "Polymarket Volume Is Being Double-Counted", Dec 2025: summing every `OrderFilled` counts each trade twice, because the taker-focused row repeats the maker rows. The `OrdersMatched` event is emitted once per match and is not double counted. Correct volume is one-sided: taker-side, maker-side, a mean of the two, or notional (contracts traded; for mint and merge, the number of complete sets). Paradigm states that per-trade cash flows differ between taker side and maker side in mint and merge matches. It says the raw sum is "roughly 2x" the correct values. Paradigm discloses an investment in Kalshi. Read through the page fetcher.
- Rocknblock, "Inside Polymarket Data": one consistent method and metric; cash flow and notional are two metrics; `OrdersMatched` or one-sided `OrderFilled` are the two valid methods. Its merge example: taker sold 6,842.98 Yes for 61.59 and the maker sold 6,842.98 No for 6,781.39. Those two cash amounts sum to the shares merged. This is the evidence for the identity in section 6.
- Earlier repo note: a parser that credits every row naming a wallet in the taker field to that wallet misbooks maker fills as the wallet's trades.

These are not primary sources for the contract. Section 2 is.

## 5. Documented: what the venue says volume is

- Gamma API (`gamma-openapi.yaml`): market fields `volume` (string), `volumeNum`, `volumeClob`, `volume24hr` and windowed variants. The spec carries no description text for any of them. So the venue's definition of market volume is undocumented. It has to be measured (section 7).
- Data API v2, analytics page: `/v2/live-volume` is "cumulative one-side taker volume in shares". The trader leaderboard is "both-sides traded volume in shares". `/v2/trades`: `size` is in shares, `price` is USDC per share. No volume field is defined for trades. Data API v1 was retired on 2 Nov 2026 (changelog), so only v2 is available.
- Both definitions say shares, not collateral. Whether the Gamma `volume` is shares, collateral, taker-side or both-sides is therefore unknown until measured.

## 6. Derived identities (arithmetic from section 2, not yet tested on data)

Let a match have rows `r`. For a row, `cash(r)` is `makerAmountFilled` if `side` is BUY, else `takerAmountFilled`. `shares(r)` is the other amount. Let `X` be the cash of the complementary part of a match and `S` the shares minted or merged.

| Match type | Sum of all row cash | Taker row cash only | Collateral that crosses the trader boundary |
|---|---|---|---|
| Pure complementary | 2X | X | X |
| Pure mint (taker BUY plus maker BUYs) | at least S, equal to S when prices exactly cross | the taker's share of S | S |
| Pure merge (taker SELL plus maker SELLs) | at least S, equal to S when prices exactly cross | the taker's share of S | S |
| Complementary plus mint | 2X + (at least S) | X + taker's mint cash | X + S |
| Complementary plus merge | 2X + (at least S) | X + taker's merge cash | X + S |

Caveat on the mint and merge rows. In a non-complementary match the taker row reports `takerFillAmount` as `makerAmountFilled` (Trading.sol lines 138 and 342), which is what the taker offered. The contract then refunds any collateral it did not need (lines 385 to 387, `_settleTakerOrder`) and sets `takerAmountFilled` to the balance change. So when the taker's limit price is better than the makers' crossing price, the row cash exceeds the cash actually spent. The "sum of row cash = S" entries are therefore lower bounds on the row sum, with equality only when the taker's limit price exactly crosses. How large the gap is has to be measured (item 4 in section 7).

So at cash level the naive sum is 2x the collateral for complementary matches and about 1x for mint and merge matches. At share level it is 2x for every match type, because each row carries its own shares and the notional counts each share once. The market-level cash overstatement is therefore `1 + f`, where `f` is the complementary share of collateral. This is why the result is an open question rather than a settled 2x. It also means that "one-sided" is not a single number in mint and merge matches: the taker side and the maker side each hold part of `S`.

## 7. What must be measured (not documented)

1. Which version each October market uses (Gamma `version`) and which exchange its fills came from. ExchangeV3 and PositionManager are documented only at integration level. Its `OrderFilled` layout and settlement are not documented in the pages read, and no source was found. See the sample rule in PREDICTIONS.md.
2. The share `f` of collateral that moves through complementary versus mint versus merge matches, per market. Nothing documented gives it.
3. The venue's reported market volume: what quantity it equals (taker cash, both-sides cash, shares, something else).
4. The collateral actually transferred in the receipts, per match, net of plumbing transfers (section 2 point 8) and fees. This includes the gap between taker-row cash and cash actually spent in mint and merge matches (caveat in section 6).
5. Whether the V2 maker-field rule from the earlier repo holds (each wallet's own fill is in the row where it is the maker field).
6. Fee size relative to volume, by market category.
7. Whether the deployed bytecode matches the source read, and pUSD decimals.
8. Contract address discrepancy: the V2 repository README lists `CtfCollateralAdapter` at `0xADa100874d00e3331D00F2007a9c336a65009718` and `NegRiskCtfCollateralAdapter` at `0xAdA200001000ef00D07553cEE7006808F895c6F1`. The docs contracts page lists `0xAdA100Db00Ca00073811820692005400218FcE1f` and `0xadA2005600Dec949baf300f4C6120000bDB6eAab`. Both sets are possibly live (an adapter replaced after launch). The receipts will show which one carries mints.

## 8. Sources and hashes

Read directly (raw GitHub, fetched 2026-11-17):

| Repo | Commit on `main` | Commit date |
|---|---|---|
| Polymarket/ctf-exchange-v2 | `ccc0596074f4dfd62c944fbca4de252893b82b4b` | 2026-04-13 |
| Polymarket/ctf-exchange | `ed5c7708b7be3aa98bf5f0c6602b57cc498e2ef4` | 2026-05-11 |
| Polymarket/neg-risk-ctf-adapter | `f78b35b0863b4308a431ca307d06f49b2ea65e78` | 2026-01-08 |

| File | SHA-256 |
|---|---|
| ctf-exchange-v2 `src/exchange/mixins/Trading.sol` | `dd8d18fca897e664583a93944b379435e6f70e84f4190c39d669b2be62596012` |
| ctf-exchange-v2 `src/exchange/mixins/Events.sol` | `50ec1ce60573fa46cf7776a9207aacbefa8881a899df706da2ce7275692c5f3b` |
| ctf-exchange-v2 `src/exchange/interfaces/ITrading.sol` | `df0a14ff32cfdfe38feb6f469d1cf5012df4fd2f658d1f1a6ce765a5a7dc8954` |
| ctf-exchange-v2 `src/adapters/CtfCollateralAdapter.sol` | `f9f85b1ac652030bf458be2130b5f977fa6670a04b2ad412241c9e9b0c444a90` |
| ctf-exchange (V1) `src/exchange/mixins/Trading.sol` | `f8ab03cb259adc49a8c38d314b286989121528f94d8be5c7f7a2fa79c2ba8af4` |

The V2 source is licensed BUSL-1.1, so it is cited by commit, path and line, not copied into this repository.

Documentation pages (docs.polymarket.com): `resources/contracts`, `changelog`, `resources/onchain-position-data`, `migrate/polymarket-v2/contract-integrations`, `market-data/public-analytics`, `concepts/order-lifecycle`, `api-spec/gamma-openapi.yaml`. Third party: Paradigm (Dec 2025), Rocknblock, and the earlier repo's note. Pages that were fetched and found silent on events or volume: `developers/CLOB/orders/onchain-order-info`, `resources/blockchain-data`, `concepts/order-lifecycle`.
