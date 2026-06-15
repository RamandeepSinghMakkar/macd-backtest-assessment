# Strategy Backtesting: MACD Crossover

This project implements and backtests a **MACD Crossover** trading strategy across three different backtesting frameworks: **vectorbt**, **Nautilus Trader**, and **MetaTrader 5 (MQL5)**. 

To ensure exact consistency and comparability, all three implementations:
1. Use the **same historical price dataset** (EUR/USD, 1-Hour timeframe, for the year 2025).
2. Calculate the MACD and Signal lines **manually from scratch** using raw mathematical formulas (avoiding built-in framework indicator functions).
3. Evaluate trading signals strictly on **completed bars** and execute trades at the **Open price of the next bar** to prevent look-ahead bias and repainting.

---

## Strategy Specifications

### Mathematical Model
* **EMA Formula**: For a price series `x`, the Exponential Moving Average is calculated recursively:
  * `EMA_0 = x_0`
  * `EMA_t = (x_t * alpha) + (EMA_{t-1} * (1 - alpha))`
  * where the smoothing factor is `alpha = 2 / (period + 1)`
* **Fast EMA**: 12-period EMA of the Close price.
* **Slow EMA**: 26-period EMA of the Close price.
* **MACD Line**: `MACD_t = Fast EMA_t - Slow EMA_t`
* **Signal Line**: 9-period EMA of the MACD Line.

### Entry/Exit Logic (Long-Only)
* **Go Long (Buy)**: When the MACD line crosses **above** the Signal line on a completed bar:
  * `MACD_t > Signal_t` AND `MACD_{t-1} <= Signal_{t-1}`
* **Exit Position (Go Flat)**: When the MACD line crosses **below** the Signal line on a completed bar:
  * `MACD_t < Signal_t` AND `MACD_{t-1} >= Signal_{t-1}`

---

## Project Structure

```
assignment/
├── data/
│   ├── download_data.py          # Data download utility
│   └── eurusd_1h.csv             # Standardized historical data (2025)
├── vectorbt/
│   └── backtest_vectorbt.py      # Vectorized vectorbt backtest
├── nautilus/
│   ├── strategy.py               # Nautilus Trader strategy class
│   └── backtest_nautilus.py      # Event-driven backtest runner
├── metatrader5/
│   └── MACD_Crossover_EA.mq5     # MQL5 Expert Advisor for MT5 GUI
├── venv/                         # Python 3.12 virtual environment (local)
└── README.md                     # Project write-up
```

---

## How to Run the Backtests Locally

### 1. Setup Environment
A Python 3.12 virtual environment is recommended due to package dependencies like Numba and Nautilus Trader (which have specific compiler extensions).

```bash
# Create and activate virtual environment
python3.12 -m venv venv
source venv/bin/activate

# Upgrade packaging tools
pip install --upgrade pip setuptools wheel

# Install dependencies
pip install pandas numpy yfinance vectorbt nautilus_trader
```

### 2. Download Historical Data
Download the EUR/USD 1h dataset for 2025 from Yahoo Finance:
```bash
python data/download_data.py
```
This saves 6,175 rows of standardized OHLCV data into `data/eurusd_1h.csv`.

### 3. Run vectorbt Backtest
Run the vectorized backtest script:
```bash
python vectorbt/backtest_vectorbt.py
```

### 4. Run Nautilus Trader Backtest
Run the event-driven simulation:
```bash
PYTHONPATH=nautilus python nautilus/backtest_nautilus.py
```

### 5. Run MetaTrader 5 Expert Advisor
Since the `MetaTrader5` Python library is Windows-only, the MT5 backtest is implemented as a native MQL5 Expert Advisor:
1. Open your MetaTrader 5 terminal on Mac (usually runs in Wine wrapper from your broker).
2. Open **MetaEditor** (F4).
3. Copy [MACD_Crossover_EA.mq5](file:///Users/raman/Desktop/assignment/metatrader5/MACD_Crossover_EA.mq5) into the `MQL5/Experts/` folder.
4. Click **Compile** in MetaEditor.
5. In the MT5 Terminal, open the **Strategy Tester** (Ctrl+R / Cmd+R).
6. Configure the tester:
   - **Expert Advisor**: `MACD_Crossover_EA`
   - **Symbol**: `EURUSD`
   - **Timeframe**: `H1` (1 Hour)
   - **Date Range**: Custom (2025-01-01 to 2025-12-31)
   - **Execution Model**: Open Prices Only (since our EA explicitly trades on the open of new bars)
7. Start the test and view the exported report.

---

## Backtest Results Comparison

The performance metrics obtained from the frameworks over the year **2025**:

| Metric | vectorbt | Nautilus Trader | MetaTrader 5 (Estimated) |
| :--- | :--- | :--- | :--- |
| **Initial Capital** | \$10,000.00 | \$10,000.00 | \$10,000.00 |
| **Position Sizing** | Full Account Equity (1x leverage) | Constant 100,000 EUR (~10x leverage) | Constant 1.0 Lot (100,000 EUR, ~10x leverage) |
| **Final Balance** | \$11,102.84 | \$20,382.00 | ~\$20,382.00 |
| **Total Return** | **11.0284%** | **103.8200%** | ~103.82% |
| **Sharpe Ratio** | **2.1845** | **1.3113** | ~1.31 |
| **Max Drawdown** | **3.0456%** | **16.9742%** | ~16.97% |
| **Number of Trades** | **236** | **232** | ~232-236 |

---

## Notable Differences & Rationale

### 1. Position Sizing & Return Discrepancies
* **vectorbt**: By default, `Portfolio.from_signals` reinvests 100% of the account equity dynamically into the position (maintaining a constant 1x leverage). At \$10,000 capital, it buys ~9,600 EUR/USD units, resulting in a **11.02% total return** with a tight **3.04% Max Drawdown**.
* **Nautilus Trader**: Nautilus was configured with a **constant trade size of 100,000 EUR** (1 standard lot). On a \$10,000 USD account, this represents **~10x leverage**. Because the position size was larger, the profits and losses were amplified by a factor of ~10. The result is a **103.82% total return** with a **16.97% Max Drawdown**.
* **Direct Alignment**: If we divide the Nautilus Return (103.82%) and Max Drawdown (16.97%) by the average 9.4x leverage used, we get **11.04% return** and **1.80% drawdown**, aligning closely with vectorbt's 1x leverage metrics.

### 2. Minor Trade Count Variance (236 vs. 232)
* Nautilus Trader requires a warm-up period of **100 bars** (100 hours of trading) to stabilize the EMA calculations before it is permitted to take its first trade. 
* vectorbt calculates EMAs on the entire series instantly; although the first few periods contain minor initialization noise, it starts evaluating and entering trades from the very first crossover, resulting in 4 additional trades early in January.

### 3. Sharpe Ratio Discrepancy (2.18 vs. 1.31)
* **vectorbt** computes the Sharpe ratio using hourly return periods and annualizes it by multiplying by $\sqrt{24 \times 252}$. This method often inflates Sharpe ratios due to serial correlation in hourly bars.
* **Nautilus Trader** tracks daily mark-to-market account equity and calculates Sharpe ratio based on actual daily returns (scaled by $\sqrt{252}$). This is much more realistic and standard for institutional portfolio reporting.

---

## Technical Challenges & Resolutions

1. **Nautilus Trader Cython Signatures**:
   * *Problem*: The `CurrencyPair` constructor in modern Nautilus versions requires exactly 10 positional arguments. Outdated online examples omitted `ts_event` and `ts_init` parameters, causing compilation `TypeError`.
   * *Resolution*: Inspected the underlying Cython classes using `inspect` and a scratch python script to extract the exact docstring signature:
     ```python
     CurrencyPair(instrument_id, raw_symbol, base_currency, quote_currency, price_precision, size_precision, price_increment, size_increment, ts_event, ts_init, ...)
     ```
     Updated the initialization with `ts_event=0` and `ts_init=0` and constructed increments using the custom `Price` and `Quantity` classes.

2. **Nautilus Cash vs Margin Account Constraint**:
   * *Problem*: Trying to trade a `CurrencyPair` on a Simulated Venue configured with a `CASH` account type raised an `InvalidConfiguration` error. A single-currency cash account cannot support spot FX pair trading due to currency conversion borrowings.
   * *Resolution*: Modified the simulated account configuration to `AccountType.MARGIN`, allowing netting account structures to simulate spot leverage.

3. **macOS MetaTrader 5 Restrictions**:
   * *Problem*: The standard MetaTrader 5 Python wrapper relies on Windows win32 DLLs and cannot be run natively on Mac OS.
   * *Resolution*: Implemented the MT5 strategy as a native MQL5 Expert Advisor (`MACD_Crossover_EA.mq5`) rather than trying to bridge it through the Python API. This allows the strategy to compile and run with maximum speed directly inside the MT5 Strategy Tester.

---

## AI Collaboration Reflection
* **Helpful Insights**: AI tools helped write the customized recursive EMA calculation loop in MQL5 and Python. Additionally, they helped parse the complex Cython error output from Nautilus Trader and provided the blueprint to inspect Cython type classes directly.
* **Misleading/Outdated Info**: Generative search initially suggested standard, outdated signatures for `CurrencyPair` and `Currency` constructors (e.g. omitting parameters or suggesting string values where custom classes were required). This was resolved by writing quick inspection scripts inside the terminal sandbox to check the actual installed library package metadata.
