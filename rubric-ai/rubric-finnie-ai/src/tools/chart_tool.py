import base64
from datetime import datetime, timedelta
import io
import logging
from typing import Any

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
import plotly.graph_objects as go

logger = logging.getLogger(__name__)

def _prepare_date_indexed_df(df: pd.DataFrame) -> pd.DataFrame:
    prepared = df.copy()
    if "Date" not in prepared.columns:
        prepared = prepared.reset_index()
        if "Datetime" in prepared.columns and "Date" not in prepared.columns:
            prepared = prepared.rename(columns={"Datetime": "Date"})
        elif "index" in prepared.columns and "Date" not in prepared.columns:
            prepared = prepared.rename(columns={"index": "Date"})
    if "Date" in prepared.columns:
        prepared["Date"] = pd.to_datetime(prepared["Date"])
    return prepared

def generate_price_chart_base64(hist_df: pd.DataFrame, ticker: str) -> str:
    """Generates a lightweight base64 PNG closing price chart."""
    if hist_df.empty:
        logger.warning("Empty DataFrame provided for base64 chart (%s)", ticker)
        return ""

    df_chart = _prepare_date_indexed_df(hist_df)
    if "Close" not in df_chart.columns or "Date" not in df_chart.columns:
        logger.error("Missing 'Close' or 'Date' column for ticker %s", ticker)
        return ""

    plt.figure(figsize=(8, 4))
    plt.plot(df_chart["Date"], df_chart["Close"], color="#00d4b6", linewidth=1.5, label="Close Price")
    plt.title(f"{ticker} Historical Trend", fontsize=12, fontweight="bold", color="#333")
    plt.xlabel("Date", fontsize=10)
    plt.ylabel("Price ($)", fontsize=10)
    plt.grid(True, linestyle="--", alpha=0.5)
    plt.legend(loc="upper left")
    plt.tight_layout()

    buf = io.BytesIO()
    plt.savefig(buf, format="png", dpi=100)
    buf.seek(0)
    encoded = base64.b64encode(buf.read()).decode("utf-8")
    plt.close()
    return f"data:image/png;base64,{encoded}"

def create_innovative_market_chart(
        df_chart: pd.DataFrame,
        ticker: str,
        chart_type: str = "Area Chart",
        requested_period: str = "max",
        *args: Any,
        **kwargs: Any,
) -> go.Figure:
    """Generates interactive Plotly price charts (Candlestick, Area, or Line)."""
    logger.info("Creating Plotly chart for %s (type=%s, period=%s)", ticker, chart_type, requested_period)
    df_plot = _prepare_date_indexed_df(df_chart) if not df_chart.empty else pd.DataFrame()

    has_series = not df_plot.empty and "Close" in df_plot.columns and "Date" in df_plot.columns
    if has_series:
        df_plot = df_plot.sort_values("Date").reset_index(drop=True)
        min_date = df_plot["Date"].min()
        max_date = df_plot["Date"].max()
    else:
        max_date = datetime.now()
        min_date = max_date - timedelta(days=365)

    fig = go.Figure()

    if has_series:
        start_price = float(df_plot["Close"].iloc[0])
        end_price = float(df_plot["Close"].iloc[-1])
        line_color = "#00e676" if end_price >= start_price else "#ff5252"

        if chart_type == "Candlestick" and {"Open", "High", "Low", "Close"}.issubset(df_plot.columns):
            fig.add_trace(
                go.Candlestick(
                    x=df_plot["Date"],
                    open=df_plot["Open"],
                    high=df_plot["High"],
                    low=df_plot["Low"],
                    close=df_plot["Close"],
                    name=ticker,
                    increasing_line_color="#00e676",
                    decreasing_line_color="#ff5252",
                    hovertemplate=(
                        "Date: %{x|%Y-%m-%d}<br>Open: $%{open:.2f}<br>"
                        "High: $%{high:.2f}<br>Low: $%{low:.2f}<br>"
                        "Close: $%{close:.2f}<extra></extra>"
                    ),
                )
            )
        elif chart_type == "Area Chart":
            fill_color = (
                "rgba(0, 230, 118, 0.15)"
                if end_price >= start_price
                else "rgba(255, 82, 82, 0.15)"
            )
            fig.add_trace(
                go.Scatter(
                    x=df_plot["Date"],
                    y=df_plot["Close"],
                    mode="lines",
                    name=f"{ticker} Area",
                    line=dict(color=line_color, width=1.8),
                    fill="tozeroy",
                    fillcolor=fill_color,
                    hovertemplate="Date: %{x|%Y-%m-%d}<br>Close: $%{y:.2f}<extra></extra>",
                )
            )
        else:
            fig.add_trace(
                go.Scatter(
                    x=df_plot["Date"],
                    y=df_plot["Close"],
                    mode="lines",
                    name=f"{ticker} Close",
                    line=dict(color=line_color, width=1.5),
                    hovertemplate="Date: %{x|%Y-%m-%d}<br>Close: $%{y:.2f}<extra></extra>",
                )
            )

    fig.update_layout(
        title=dict(
            text=f"<b>{ticker}</b> — Market Price Action",
            font=dict(size=16, color="#f8fafc"),
        ),
        xaxis=dict(
            showgrid=True,
            gridcolor="rgba(255, 255, 255, 0.04)",
            range=[min_date, max_date],
            autorange=False,
            rangeslider=dict(visible=False),
            type="date",
        ),
        yaxis=dict(
            showgrid=True,
            gridcolor="rgba(255, 255, 255, 0.04)",
            side="right",
            tickprefix="$",
            tickformat=".2f",
            tickfont=dict(color="#9ca3af"),
            autorange=True,
        ),
        hovermode="x unified",
        paper_bgcolor="#111827",
        plot_bgcolor="#111827",
        margin=dict(l=20, r=40, t=50, b=30),
    )

    return fig