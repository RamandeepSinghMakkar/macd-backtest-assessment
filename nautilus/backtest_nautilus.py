import os
from decimal import Decimal
import pandas as pd

from nautilus_trader.backtest.engine import BacktestEngine
from nautilus_trader.backtest.config import BacktestEngineConfig
from nautilus_trader.model.data import BarType, BarSpecification
from nautilus_trader.model.enums import BarAggregation, PriceType, OmsType, AccountType
from nautilus_trader.model.identifiers import InstrumentId, Venue, Symbol, AccountId
from nautilus_trader.model.instruments import CurrencyPair
from nautilus_trader.model.objects import Money, Currency, Price, Quantity
from nautilus_trader.persistence.wranglers import BarDataWrangler

from strategy import MACDCrossover, MACDCrossoverConfig

def run_backtest():
    csv_path = "data/eurusd_1h.csv"
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"Data file not found at {csv_path}. Please run download_data.py first.")

    # Load historical bar data
    df = pd.read_csv(csv_path)
    df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True)
    df.set_index('timestamp', inplace=True)

    # Initialize Nautilus Backtest Engine
    engine = BacktestEngine(config=BacktestEngineConfig(trader_id="BACKTESTER-01"))

    # Configure a simulated netting venue with a margin account. 
    # Spot FX trading involves currency pairs that require margin rather than cash.
    venue = Venue("SIM")
    engine.add_venue(
        venue=venue,
        oms_type=OmsType.NETTING,
        account_type=AccountType.MARGIN,
        base_currency=Currency.from_str("USD"),
        starting_balances=[Money(10000, Currency.from_str("USD"))]
    )

    # Register the EUR/USD instrument. 
    # Custom increment and lot size parameters are required by the CurrencyPair constructor.
    instrument_id = InstrumentId.from_str("EURUSD.SIM")
    instrument = CurrencyPair(
        instrument_id=instrument_id,
        raw_symbol=Symbol("EURUSD"),
        base_currency=Currency.from_str("EUR"),
        quote_currency=Currency.from_str("USD"),
        price_precision=5,
        size_precision=2,
        price_increment=Price.from_str("0.00001"),
        size_increment=Quantity.from_str("0.01"),
        ts_event=0,
        ts_init=0,
        lot_size=Quantity.from_str("1.0")
    )
    engine.add_instrument(instrument)

    # Define the 1-hour bar specification matching our dataset
    bar_type = BarType(
        instrument_id=instrument_id,
        bar_spec=BarSpecification(
            step=1,
            aggregation=BarAggregation.HOUR,
            price_type=PriceType.LAST
        )
    )

    # Parse pandas DataFrame into Nautilus Bar objects.
    # Yahoo Finance bars are timestamped at the START of the hour. We apply a 1-hour 
    # delay delta (3.6 trillion nanoseconds) to prevent look-ahead bias, ensuring 
    # the engine receives the bar only after the hour has completed.
    wrangler = BarDataWrangler(bar_type=bar_type, instrument=instrument)
    bars = wrangler.process(df, ts_init_delta=3_600_000_000_000)
    
    engine.add_data(bars)

    # Initialize the MACD Crossover Strategy with standard 1 lot position size
    strategy_config = MACDCrossoverConfig(
        instrument_id=instrument_id,
        bar_type=bar_type,
        trade_size=Decimal("100000")  # Standard 1 lot (100k base units of EUR)
    )
    strategy = MACDCrossover(config=strategy_config)
    engine.add_strategy(strategy)

    print("Running Nautilus Trader backtest...")
    engine.run()
    print("Backtest finished.")

    # Extract performance metrics for reporting
    portfolio = engine.portfolio
    analyzer = portfolio.analyzer
    
    stats_pnls = analyzer.get_performance_stats_pnls()
    stats_general = analyzer.get_performance_stats_general()
    stats_returns = analyzer.get_performance_stats_returns()
    
    account_report = engine.trader.generate_account_report(venue)
    positions_report = engine.trader.generate_positions_report()
    fills_report = engine.trader.generate_order_fills_report()
    
    num_trades = len(fills_report) // 2 if fills_report is not None else 0
    
    print("\n========================================")
    print("      NAUTILUS TRADER BACKTEST RESULTS  ")
    print("========================================")
    initial_capital = 10000.0
    final_balance = portfolio.account(venue, AccountId("SIM-001")).balance_total(Currency.from_str("USD")).as_double()
    total_return = ((final_balance - initial_capital) / initial_capital) * 100.0
    
    sharpe_ratio = 0.0
    if stats_returns and "Sharpe Ratio (252 days)" in stats_returns:
        sharpe_ratio = float(stats_returns["Sharpe Ratio (252 days)"])
        
    # Calculate Maximum Drawdown using the historical account balance trajectory.
    import numpy as np
    max_drawdown = 0.0
    if account_report is not None and not account_report.empty:
        balances = account_report['total'].astype(float).values
        peaks = np.maximum.accumulate(balances)
        drawdowns = np.where(peaks > 0, (balances - peaks) / peaks, 0.0)
        max_drawdown = abs(drawdowns.min()) * 100.0

    print(f"Initial Capital:   ${initial_capital:,.2f}")
    print(f"Final Balance:     ${final_balance:,.2f}")
    print(f"Total Return:      {total_return:.4f}%")
    print(f"Sharpe Ratio:      {sharpe_ratio:.4f}")
    print(f"Max Drawdown:      {max_drawdown:.4f}%")
    print(f"Number of Trades:  {num_trades}")
    print("========================================")
    
    print("\nNautilus Trader Account Summary:")
    print(account_report)
    
    print("\nNautilus Trader Positions Summary:")
    print(positions_report)

    engine.reset()
    engine.dispose()

if __name__ == "__main__":
    run_backtest()
