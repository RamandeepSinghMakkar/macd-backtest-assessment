import os
import pandas as pd
import numpy as np
import vectorbt as vbt

def compute_ema(prices, period):
    alpha = 2.0 / (period + 1.0)
    ema = np.zeros_like(prices)
    if len(prices) > 0:
        ema[0] = prices[0]
        for i in range(1, len(prices)):
            ema[i] = prices[i] * alpha + ema[i-1] * (1.0 - alpha)
    return ema

def run_backtest():
    csv_path = "data/eurusd_1h.csv"
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"Data file not found at {csv_path}. Please run download_data.py first.")
        
    # Load historical backtest data
    df = pd.read_csv(csv_path)
    df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True)
    df.set_index('timestamp', inplace=True)
    
    close_prices = df['close'].values
    
    # Calculate custom EMAs, MACD line, and Signal line manually.
    fast_ema = compute_ema(close_prices, 12)
    slow_ema = compute_ema(close_prices, 26)
    macd_line = fast_ema - slow_ema
    signal_line = compute_ema(macd_line, 9)
    
    # Store technical indicators in the DataFrame for vectorized signal generation.
    df['fast_ema'] = fast_ema
    df['slow_ema'] = slow_ema
    df['macd'] = macd_line
    df['signal'] = signal_line
    
    # Vectorized crossover logic. 
    # Long Entry when MACD crosses above Signal.
    df['prev_macd'] = df['macd'].shift(1)
    df['prev_signal'] = df['signal'].shift(1)
    
    entries = (df['macd'] > df['signal']) & (df['prev_macd'] <= df['prev_signal'])
    exits = (df['macd'] < df['signal']) & (df['prev_macd'] >= df['prev_signal'])
    
    # Handle initial NaN boolean values
    entries = entries.fillna(False)
    exits = exits.fillna(False)
    
    # Initialize vectorbt Portfolio from signals. 
    # Starting capital is $10,000 with zero fees/slippage to match the simulated venues in other platforms.
    pf = vbt.Portfolio.from_signals(
        close=df['close'],
        entries=entries,
        exits=exits,
        init_cash=10000.0,
        fees=0.0,
        slippage=0.0,
        freq='1h'
    )
    
    # Extract and display performance metrics
    total_return = pf.total_return() * 100
    sharpe_ratio = pf.sharpe_ratio()
    max_drawdown = pf.max_drawdown() * 100
    num_trades = pf.trades.count()
    
    print("========================================")
    print("        VECTORBT BACKTEST RESULTS       ")
    print("========================================")
    print(f"Total Return:      {total_return:.4f}%")
    print(f"Sharpe Ratio:      {sharpe_ratio:.4f}")
    print(f"Max Drawdown:      {max_drawdown:.4f}%")
    print(f"Number of Trades:  {num_trades}")
    print("========================================")
    
    print("\nVectorbt Full Portfolio Stats:")
    print(pf.stats())

if __name__ == "__main__":
    run_backtest()
