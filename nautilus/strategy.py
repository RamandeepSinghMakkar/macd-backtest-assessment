from decimal import Decimal
from nautilus_trader.config import StrategyConfig
from nautilus_trader.model.data import Bar, BarType
from nautilus_trader.model.enums import OrderSide
from nautilus_trader.model.identifiers import InstrumentId
from nautilus_trader.trading.strategy import Strategy

class MACDCrossoverConfig(StrategyConfig, frozen=True):
    instrument_id: InstrumentId
    bar_type: BarType
    trade_size: Decimal

class MACDCrossover(Strategy):
    def __init__(self, config: MACDCrossoverConfig):
        super().__init__(config)
        self.close_prices = []
        self.instrument = None

    def on_start(self):
        # Retrieve instrument metadata from the engine cache.
        self.instrument = self.cache.instrument(self.config.instrument_id)
        if self.instrument is None:
            self.log.error(f"Could not find instrument for ID: {self.config.instrument_id}")
            self.stop()
            return
            
        # Subscribe to the specified bar type to receive on_bar events.
        self.subscribe_bars(self.config.bar_type)

    def compute_ema(self, prices: list, period: int) -> list:
        alpha = 2.0 / (period + 1.0)
        ema = [0.0] * len(prices)
        ema[0] = prices[0]
        for i in range(1, len(prices)):
            ema[i] = prices[i] * alpha + ema[i-1] * (1.0 - alpha)
        return ema

    def on_bar(self, bar: Bar):
        # Store the close price of the newly completed bar for EMA calculations.
        self.close_prices.append(float(bar.close))
        
        # Ensure a minimum amount of data is available to stabilize the 26-period 
        # slow EMA and 9-period signal EMA. A 100-bar warm-up period is used.
        if len(self.close_prices) < 100:
            return
            
        # Calculate custom EMAs, MACD line, and Signal line manually.
        fast_ema = self.compute_ema(self.close_prices, 12)
        slow_ema = self.compute_ema(self.close_prices, 26)
        macd_line = [f - s for f, s in zip(fast_ema, slow_ema)]
        signal_line = self.compute_ema(macd_line, 9)
        
        current_macd = macd_line[-1]
        current_signal = signal_line[-1]
        
        prev_macd = macd_line[-2]
        prev_signal = signal_line[-2]
        
        # Crossover logic for Long Entry: MACD crosses above Signal.
        if prev_macd <= prev_signal and current_macd > current_signal:
            if self.portfolio.is_flat(self.config.instrument_id):
                qty = self.instrument.make_qty(self.config.trade_size)
                order = self.order_factory.market(
                    instrument_id=self.config.instrument_id,
                    order_side=OrderSide.BUY,
                    quantity=qty
                )
                self.log.info(f"Submitting BUY order for {qty} units at close {bar.close}")
                self.submit_order(order)
                
        # Crossover logic for Exit: MACD crosses below Signal.
        elif prev_macd >= prev_signal and current_macd < current_signal:
            if self.portfolio.is_net_long(self.config.instrument_id):
                qty = self.instrument.make_qty(self.config.trade_size)
                order = self.order_factory.market(
                    instrument_id=self.config.instrument_id,
                    order_side=OrderSide.SELL,
                    quantity=qty
                )
                self.log.info(f"Submitting SELL order for {qty} units at close {bar.close}")
                self.submit_order(order)

    def on_stop(self):
        pass
