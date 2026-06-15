import os
import yfinance as yf
import pandas as pd

def download_data():
    ticker = "EURUSD=X"
    start_date = "2025-01-01"
    end_date = "2026-01-01"
    
    print(f"Downloading hourly data for {ticker} from {start_date} to {end_date}...")
    
    df = yf.download(ticker, start=start_date, end=end_date, interval="1h")
    
    if df.empty:
        raise ValueError(f"No data downloaded for {ticker}. Please check the ticker or date range.")
        
    print(f"Downloaded {len(df)} rows.")
    
    # Flatten MultiIndex columns returned by Yahoo Finance to ensure standard DataFrame structure.
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
        
    df = df.reset_index()
    
    # Standardize column names for downstream backtesting frameworks.
    rename_map = {
        'Datetime': 'timestamp',
        'Date': 'timestamp',
        'Open': 'open',
        'High': 'high',
        'Low': 'low',
        'Close': 'close',
        'Volume': 'volume'
    }
    df = df.rename(columns=rename_map)
    
    cols_to_keep = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
    df = df[cols_to_keep]
    
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df = df.sort_values('timestamp').reset_index(drop=True)
    
    os.makedirs("data", exist_ok=True)
    
    output_path = "data/eurusd_1h.csv"
    df.to_csv(output_path, index=False)
    print(f"Data saved to {output_path} successfully!")
    print(f"Data range: {df['timestamp'].min()} to {df['timestamp'].max()}")
    print(df.head())

if __name__ == "__main__":
    download_data()
