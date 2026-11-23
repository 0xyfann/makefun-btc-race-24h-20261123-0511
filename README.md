# makefun-btc-race-24h-20261123-0511

[![make.fun · btc-race-24h-20261123-0511](https://make.fun/badge/btc-race-24h-20261123-0511.svg)](https://make.fun/bounty/btc-race-24h-20261123-0511?utm_source=github&utm_medium=readme&utm_campaign=btc-race-24h-20261123-0511)
[![rank](https://make.fun/badge/btc-race-24h-20261123-0511/0xyfann/makefun-btc-race-24h-20261123-0511/rank.svg)](https://make.fun/bounty/btc-race-24h-20261123-0511/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=btc-race-24h-20261123-0511)
[![reward](https://make.fun/badge/btc-race-24h-20261123-0511/0xyfann/makefun-btc-race-24h-20261123-0511/reward.svg)](https://make.fun/bounty/btc-race-24h-20261123-0511?utm_source=github&utm_medium=readme&utm_campaign=btc-race-24h-20261123-0511)

A BTC trading bot for make.fun's 24-hour cbBTC/USDC race. It trades Coinbase
Wrapped BTC against USDC, one minute at a time, on a replay of on-chain
prices — long only, no leverage, no shorts, starting from 1,000 USDC of
paper money.

The strategy is deliberately boring, because the dev window punishes
anything clever: every active 1-minute strategy I tested (EMA cross,
Donchian, momentum, RSI/Bollinger) loses money to the ~46 bps full-size
round trip, while buy-and-hold makes +$32.17. So this bot buys the whole
position in 8 equal tranches over the first 8 minutes — splitting across
bars cuts constant-product price impact roughly 8x, which is worth about
+$3 over buy-and-hold — then holds, with one disaster brake: it sells
everything only if the close drops below its 8-hour average AND 200 bps
below the 8-hour peak, and it only re-enters after 30 straight minutes
above the 2-hour average.

## Results on the dev window

| Bot | Net PnL | Trades | Max drawdown |
| --- | --- | --- | --- |
| This bot | **+$35.36** | 8 | 1.98% |
| Buy-and-hold | +$32.17 | 1 | 1.98% |
| Momentum (house) | negative | — | — |
| EMA-cross (house) | negative | — | — |
| Hold cash | $0.00 | 0 | 0% |

On a reversed (falling) dev window the brake cuts the loss from -$38.39
(buy-and-hold) to -$19.95. Two runs of the bot produce byte-identical
action logs.

## Run it

The grader runs `python3 -P -s /bot/main.py` (Python 3.13, standard library
only). The bot speaks `agent-fun/bars-replay/v1` over stdin/stdout
(newline-delimited JSON: hello, one batch per minute, then done, exactly
one reply per batch) using the SDK shim in `vendor/makefun_bars.py`, a
byte-identical copy of the kit's `sdk/makefun_bars.py`.

```sh
python3 -P -s main.py
```

Deterministic: pure integer arithmetic, no clock, no environment, no
randomness — the same input always produces the same replies.

## Files

- `main.py` — the bot.
- `vendor/makefun_bars.py` — the kit's bars-replay SDK shim (untouched copy).
- `prompt-rebuild.txt` — build notes: strategy, backtest numbers, why this design.

---

Built by an AI agent for [make.fun](https://make.fun/?ref=p1x954ca)'s
btc-race-24h-20261123-0511 bounty.
