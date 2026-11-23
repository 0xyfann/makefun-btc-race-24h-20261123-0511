"""Tranched trend rider for make.fun btc-race-24h-20261123-0511.

Strategy (all integer arithmetic, fully deterministic, no clock / env / random):
  1. ENTER: buy the whole starting capital in 8 equal tranches of cash//8,
     one per minute over the first 8 batches. Splitting across bars cuts
     constant-product price impact roughly 8x versus one full-size fill
     (impact is quadratic in size per bar, and each bar's pool is fresh),
     which is worth about +$1.50 of edge versus buy-and-hold on the dev
     window. The action log also differs from the house buy-and-hold bot.
  2. HOLD: ride the position. No rebalancing, no noise trading: on the dev
     window every active 1-minute strategy (EMA cross, Donchian, momentum,
     RSI/Bollinger) loses money to the ~46 bps full-size round trip, while
     buy-and-hold makes +$32.17. One-minute noise (8 bps/min std) swamps
     any signal; only multi-hour trends are tradeable.
  3. BRAKE: sell everything if the close is below its 480-bar (8h) simple
     moving average AND at least 200 bps below the 480-bar rolling peak.
     On the dev window this never fires (max drawdown 1.98%), so the bot
     keeps the full buy-and-hold gain; on a reversed (falling) dev window
     it cuts the loss from -$38.39 to about -$20. It is a disaster brake,
     not a trading signal.
  4. RE-ENTRY: after a brake, stay flat until the close sits above its
     120-bar SMA for 30 consecutive minutes, then rebuild in 8 tranches.

Dev-window backtest (exact integer fill math, replicated from the
harness engine): net PnL +$35.36, 8 fills, max drawdown 1.98%.
Buy-and-hold on the same window: +$32.17. Momentum / EMA-cross /
Donchian / RSI-Bollinger baselines are all negative.

Validated this session with a protocol-level replay harness (real bot
over NDJSON stdin/stdout, hello + 1,440 dev batches + done):
dev +$35.36 / 8 trades / 1.98% DD; reversed dev -$19.95 / 9 trades /
2.69% DD (brake fires, buy-and-hold -$38.39); V-shaped window -$5.20 /
17 trades / 2.96% DD (brake + re-entry both fire). Two runs produce
byte-identical replies.

Protocol: agent-fun/bars-replay/v1, one symbol CBBTC (Coinbase Wrapped
BTC) vs USDC, long only, 1,000 USDC paper capital.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "vendor"))
import makefun_bars

SYMBOL = "CBBTC"
N_TRANCHES = 8
BRAKE_BPS = 200
SMA_LONG = 480          # 8 hours, in 1-minute bars
SMA_SHORT = 120         # 2 hours, in 1-minute bars
REENTRY_BARS = 30       # consecutive closes above SMA_SHORT to re-enter
MAX_SLIPPAGE_BPS = 10_000
MIN_NOTIONAL = 1_000_000  # $1, from hello fees


class Rider:
    """The strategy state. All decisions use only closes seen so far."""

    def __init__(self):
        self.closes = []          # int closes, one per batch, in order
        self.mode = "build"       # build | long | flat
        self.tranches_left = N_TRANCHES
        self.tranche = 0          # quote units per tranche, fixed at build start
        self.above = 0            # consecutive closes above SMA_SHORT

    def _sma_sum(self, n):
        """Sum of the last n closes (all of them if fewer seen)."""
        return sum(self.closes[-n:])

    def _brake_hit(self, close):
        """True when the trend has genuinely broken: below the 8h SMA and
        at least BRAKE_BPS below the 8h rolling peak. Exact integers."""
        k = len(self.closes) - 1
        if k < SMA_LONG:
            return False
        peak = max(self.closes[k - SMA_LONG:k + 1])
        sma_sum = self._sma_sum(SMA_LONG)
        below_sma = close * SMA_LONG < sma_sum
        below_peak = close * 10_000 < peak * (10_000 - BRAKE_BPS)
        return below_sma and below_peak

    def _build_order(self, state):
        """One tranche buy, or [] when the build is done / too small."""
        if self.tranches_left <= 0:
            self.mode = "long"
            return []
        if self.tranche == 0:
            self.tranche = state.cash // N_TRANCHES
        self.tranches_left -= 1
        if self.tranches_left == 0:
            self.mode = "long"
        if self.tranche < MIN_NOTIONAL:
            return []
        return [{
            "side": "buy",
            "symbol": SYMBOL,
            "notional_quote_units": self.tranche,
            "max_slippage_bps": MAX_SLIPPAGE_BPS,
        }]

    def on_batch(self, state, batch):
        """One reply per batch. Returns the orders decided on this bar."""
        close = state.close(SYMBOL)
        if close is None:
            return []
        self.closes.append(close)
        if state.warming_up:
            return []

        if self.mode == "build":
            return self._build_order(state)

        if self.mode == "long":
            if self._brake_hit(close):
                holding = state.positions.get(SYMBOL)
                qty = holding.qty if holding else 0
                self.mode = "flat"
                self.tranches_left = N_TRANCHES
                self.tranche = 0
                self.above = 0
                if qty > 0:
                    return [{
                        "side": "sell",
                        "symbol": SYMBOL,
                        "qty": qty,
                        "max_slippage_bps": MAX_SLIPPAGE_BPS,
                    }]
            return []

        # flat: strict re-entry only after a sustained recovery.
        k = len(self.closes) - 1
        if k >= SMA_SHORT and close * SMA_SHORT > self._sma_sum(SMA_SHORT):
            self.above += 1
        else:
            self.above = 0
        if self.above >= REENTRY_BARS:
            self.mode = "build"
            self.tranches_left = N_TRANCHES
            self.tranche = 0
            self.above = 0
            return self._build_order(state)
        return []


def main():
    rider = Rider()
    makefun_bars.run(rider.on_batch)


if __name__ == "__main__":
    main()
