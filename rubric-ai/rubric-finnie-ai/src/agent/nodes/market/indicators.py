# src/agent/nodes/market/indicators.py

import pandas as pd

def calculate_rsi(series: pd.Series, period: int = 14) -> float:
    """Computes the Relative Strength Index (RSI) over the given period."""
    if len(series) < period + 1:
        return 50.0

    delta = series.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)

    avg_gain = gain.rolling(window=period).mean().iloc[-1]
    avg_loss = loss.rolling(window=period).mean().iloc[-1]

    if pd.isna(avg_loss) or avg_loss == 0:
        return 100.0
    if pd.isna(avg_gain) or avg_gain == 0:
        return 0.0

    rs = avg_gain / avg_loss
    rsi = 100.0 - (100.0 / (1.0 + rs))
    return round(float(rsi), 2)

def _compute_macd_lines(series: pd.Series) -> tuple[pd.Series, pd.Series]:
    ema_12 = series.ewm(span=12, adjust=False).mean()
    ema_26 = series.ewm(span=26, adjust=False).mean()
    macd_line = ema_12 - ema_26
    signal_line = macd_line.ewm(span=9, adjust=False).mean()
    return macd_line, signal_line

def calculate_macd(series: pd.Series) -> str:
    """Computes MACD crossover status ('Bullish Crossover', 'Bearish Crossover', or 'Neutral')."""
    if len(series) < 26:
        return "Neutral"

    macd_line, signal_line = _compute_macd_lines(series)
    latest_macd = macd_line.iloc[-1]
    latest_signal = signal_line.iloc[-1]

    if latest_macd > latest_signal:
        return "Bullish Crossover"
    if latest_macd < latest_signal:
        return "Bearish Crossover"
    return "Neutral"