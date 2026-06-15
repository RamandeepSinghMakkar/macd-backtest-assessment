//+------------------------------------------------------------------+
//|                                           MACD_Crossover_EA.mq5   |
//|                                  Copyright 2026, Antigravity AI   |
//|                                             https://google.com    |
//|                                                                  |
//| A custom MACD Crossover Expert Advisor that computes EMAs and    |
//| MACD/Signal lines manually (without using built-in iMACD) to     |
//| run a clean backtest in MetaTrader 5.                            |
//+------------------------------------------------------------------+
#property copyright "Copyright 2026, Antigravity AI"
#property link      "https://google.com"
#property version   "1.00"

#include <Trade\Trade.mqh>
CTrade trade;

// Strategy configuration parameters
input group "=== Strategy Parameters ==="
input int      FastMAPeriod   = 12;      // Fast EMA Period
input int      SlowMAPeriod   = 26;      // Slow EMA Period
input int      SignalPeriod   = 9;       // Signal Line Period
input double   LotSize        = 1.0;     // Trade Lot Size (1.0 lot = 100k units)

// State variables
datetime last_bar_time = 0;

//+------------------------------------------------------------------+
//| Expert initialization function                                   |
//+------------------------------------------------------------------+
int OnInit()
{
   Print("MACD Crossover EA initialized. Parameters: Fast=", FastMAPeriod, ", Slow=", SlowMAPeriod, ", Signal=", SignalPeriod, ", Lot=", LotSize);
   last_bar_time = 0;
   return(INIT_SUCCEEDED);
}

//+------------------------------------------------------------------+
//| Expert deinitialization function                                 |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
   Print("MACD Crossover EA deinitialized. Reason code: ", reason);
}

//+------------------------------------------------------------------+
//| Calculate EMA manually on a given array of prices                |
//+------------------------------------------------------------------+
void CalculateEMA(const double &prices[], int period, double &ema[])
{
   int size = ArraySize(prices);
   ArrayResize(ema, size);
   if(size == 0) return;
   
   double alpha = 2.0 / (period + 1.0);
   ema[0] = prices[0]; // Initialize the first EMA value with the raw starting price.
   
   for(int i = 1; i < size; i++)
   {
      ema[i] = prices[i] * alpha + ema[i-1] * (1.0 - alpha);
   }
}

//+------------------------------------------------------------------+
//| Check if a position is open on this symbol                       |
//+------------------------------------------------------------------+
bool IsPositionOpen()
{
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      if(PositionGetSymbol(i) == _Symbol)
      {
         return true;
      }
   }
   return false;
}

//+------------------------------------------------------------------+
//| Expert tick function                                             |
//+------------------------------------------------------------------+
void OnTick()
{
   // Ensure trading logic executes strictly once per completed bar.
   datetime current_bar_time = iTime(_Symbol, _Period, 0);
   if(current_bar_time == last_bar_time)
   {
      return; // Not a new bar
   }
   
   // Record bar timestamp to prevent duplicate executions.
   last_bar_time = current_bar_time;
   
   // Fetch recent historical close prices.
   // Index 149 is the forming bar, 148 is the latest completed bar, and 147 is the previous completed bar.
   double close_prices[];
   int copied = CopyClose(_Symbol, _Period, 0, 150, close_prices);
   if(copied < 150)
   {
      Print("Not enough historical bars. Copied: ", copied, "/150");
      last_bar_time = 0; // Retry next tick
      return;
   }
   
   double fast_ema[];
   double slow_ema[];
   double macd_line[];
   double signal_line[];
   
   // Calculate EMAs manually using the custom recursive function.
   CalculateEMA(close_prices, FastMAPeriod, fast_ema);
   CalculateEMA(close_prices, SlowMAPeriod, slow_ema);
   
   // Calculate MACD Line (Fast EMA - Slow EMA)
   ArrayResize(macd_line, 150);
   for(int i = 0; i < 150; i++)
   {
      macd_line[i] = fast_ema[i] - slow_ema[i];
   }
   
   // Calculate Signal Line (EMA of MACD Line)
   CalculateEMA(macd_line, SignalPeriod, signal_line);
   
   // Retrieve MACD and Signal values for crossover comparison.
   double current_macd   = macd_line[148];
   double current_signal = signal_line[148];
   double prev_macd      = macd_line[147];
   double prev_signal    = signal_line[147];
   
   // Log completed bar metrics for debugging.
   PrintFormat("Completed Bar Close: %.5f | MACD: %.6f | Signal: %.6f", close_prices[148], current_macd, current_signal);
   
   // Evaluate MACD vs Signal crossover logic.
   bool buy_crossover  = (prev_macd <= prev_signal) && (current_macd > current_signal);
   bool sell_crossover = (prev_macd >= prev_signal) && (current_macd < current_signal);
   
   // Trading Logic
   if(buy_crossover)
   {
      if(!IsPositionOpen())
      {
         Print("BUY Crossover detected. Placing Buy order...");
         trade.Buy(LotSize, _Symbol, 0, 0, 0, "MACD Crossover BUY");
      }
   }
   else if(sell_crossover)
   {
      if(IsPositionOpen())
      {
         Print("SELL Crossover detected. Closing current position...");
         trade.PositionClose(_Symbol);
      }
   }
}
//+------------------------------------------------------------------+
