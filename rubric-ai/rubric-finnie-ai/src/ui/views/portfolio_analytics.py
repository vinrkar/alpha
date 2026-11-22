from datetime import date, timedelta
import uuid
from typing import Any

import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

from src.services.market_data_service import fetch_live_sector
from src.services.quant_service import (
    calculate_beta,
    calculate_portfolio_metrics,
    calculate_value_at_risk,
)
from src.tools.yfinance_tool import fetch_historical_prices, fetch_live_market_data
from src.ui.components.layouts import open_stock_modal
from src.ui.components.styles import (
    render_data_header_card,
    render_kpi_card,
    render_mini_kpi_card,
    render_subheader_card,
)
from src.ui.components.tables import (
    render_row_divider,
    render_sortable_table,
    render_table_cell,
)

HOLDINGS_COLUMNS: list[dict[str, Any]] = [
    {"key": "idx", "label": "#", "width": 0.5},
    {"key": "ticker", "label": "TICKER", "width": 1.4},
    {"key": "isin", "label": "ISIN", "width": 1.8},
    {"key": "name", "label": "NAME", "width": 3.0},
    {"key": "shares", "label": "SHARES", "width": 1.1},
    {"key": "avg_cost", "label": "AVG UNIT PRICE", "width": 2.1},
    {"key": "price", "label": "CURR PRICE", "width": 1.5},
    {"key": "cost", "label": "COST", "width": 1.4},
    {"key": "market_value", "label": "MKT VAL", "width": 1.4},
    {"key": "pct_port", "label": "% PRTF", "width": 1.4},
    {"key": "gain_loss", "label": "G/L", "width": 1.4},
    {"key": "sector", "label": "SECT", "width": 2.0},
    {"key": "exchange", "label": "EXCH", "width": 1.1},
]

def _simulate_benchmark_returns(risk_profile: str, days: int = 252) -> pd.Series:
    rng = np.random.default_rng(42)
    if risk_profile == "Aggressive Growth":
        return pd.Series(rng.normal(0.0008, 0.02, days))
    if risk_profile in {"Conservative", "Dividend Growth"}:
        return pd.Series(rng.normal(0.0003, 0.008, days))
    return pd.Series(rng.normal(0.0005, 0.012, days))

def render_portfolio_analytics_tab(active_user_id: str, active_user_data: dict[str, Any]) -> None:
    user_name = active_user_data.get("name", "User")
    risk_profile = active_user_data.get("risk_tolerance", "Standard")
    horizon = active_user_data.get("investment_horizon", "N/A")

    render_subheader_card(
        f"💼 Active Portfolio: {user_name} ({risk_profile})",
        subtitle=f"Investment Horizon: {horizon}",
    )

    holdings_dict = active_user_data.get("holdings", {})
    if not holdings_dict:
        st.info("No active holdings found for this profile.")
        return

    total_cost_sum = 0.0
    total_market_val_sum = 0.0
    computed_holdings: list[dict[str, Any]] = []

    for ticker, info in holdings_dict.items():
        shares = float(info.get("shares", 0))
        avg_cost = float(info.get("avg_cost", 0.0))
        t_cost = shares * avg_cost
        total_cost_sum += t_cost

        live_res = fetch_live_market_data(ticker)
        curr_price = (
            float(live_res.get("current_price", avg_cost))
            if isinstance(live_res, dict)
            else avg_cost
        )
        mkt_val = shares * curr_price
        total_market_val_sum += mkt_val

        computed_holdings.append(
            {
                "ticker": ticker,
                "info": info,
                "shares": shares,
                "avg_cost": avg_cost,
                "total_cost": t_cost,
                "current_price": curr_price,
                "market_value": mkt_val,
                "sector": fetch_live_sector(ticker),
            }
        )

    total_gain_loss = total_market_val_sum - total_cost_sum
    pct_chg = (
        ((total_market_val_sum - total_cost_sum) / total_cost_sum) * 100
        if total_cost_sum > 0
        else 0.0
    )

    daily_returns = _simulate_benchmark_returns(risk_profile)
    quant_metrics = calculate_portfolio_metrics(daily_returns)
    var_95 = calculate_value_at_risk(daily_returns, confidence_level=0.95)

    spy_df = fetch_historical_prices(
        "SPY",
        start=str(date.today() - timedelta(days=365)),
        end=str(date.today()),
    )
    spy_returns = spy_df["Close"].pct_change().dropna() if not spy_df.empty else pd.Series([0.0])
    portfolio_beta = calculate_beta(daily_returns, spy_returns)

    m_row1 = st.columns(3, gap="medium")
    with m_row1[0]:
        render_kpi_card("Total Cost Basis", f"${total_cost_sum:,.2f}")
    with m_row1[1]:
        mv_color = "#00e676" if pct_chg >= 0 else "#ff5252"
        chg_sign = "+" if pct_chg >= 0 else ""
        render_kpi_card(
            "Portfolio Market Value",
            f"${total_market_val_sum:,.2f}",
            f"<div style='font-size: 12px; font-weight: 600; color: {mv_color}; margin-top: 4px;'>{chg_sign}{pct_chg:,.2f}%</div>",
        )
    with m_row1[2]:
        gl_color = "#00e676" if total_gain_loss >= 0 else "#ff5252"
        gl_str = f"${total_gain_loss:,.2f}" if total_gain_loss >= 0 else f"(${abs(total_gain_loss):,.2f})"
        render_kpi_card(
            "Total Unrealized Gain/Loss",
            f"<span style='color: {gl_color};'>{gl_str}</span>",
        )

    st.markdown("<div style='margin-top: 12px;'></div>", unsafe_allow_html=True)

    m_row2 = st.columns(5, gap="small")
    mini_metrics = [
        ("Sharpe Ratio", f"{quant_metrics['sharpe_ratio']:,.2f}", "Risk-Adjusted", "#38bdf8"),
        ("Ann. Volatility", f"{quant_metrics['annualized_volatility'] * 100:,.2f}%", "Risk Metric", "#f8fafc"),
        ("Max Drawdown", f"{quant_metrics['max_drawdown'] * 100:,.2f}%", "Downside", "#ff5252"),
        ("Value at Risk (95%)", f"{var_95 * 100:,.2f}%", "Historical VaR", "#fbbf24"),
        ("Portfolio Beta", f"{portfolio_beta:,.2f}", "vs. S&P 500", "#38bdf8"),
    ]
    for col, (label, val, sub, val_col) in zip(m_row2, mini_metrics):
        with col:
            render_mini_kpi_card(label, val, sub, val_col)

    st.markdown(
        "<hr style='margin: 16px 0 18px 0; border: 0; height: 1px; background-color: rgba(255, 255, 255, 0.15);'>",
        unsafe_allow_html=True,
    )

    table_rows: list[dict[str, Any]] = []
    for item in computed_holdings:
        mkt_val = item["market_value"]
        t_cost = item["total_cost"]
        pct_port = (mkt_val / total_market_val_sum * 100) if total_market_val_sum > 0 else 0.0
        info = item["info"]
        table_rows.append(
            {
                "ticker": item["ticker"],
                "isin": info.get("isin", "N/A"),
                "name": info.get("name", item["ticker"]),
                "shares": item["shares"],
                "avg_cost": item["avg_cost"],
                "price": item["current_price"],
                "cost": t_cost,
                "market_value": mkt_val,
                "pct_port": pct_port,
                "gain_loss": mkt_val - t_cost,
                "sector": item["sector"],
                "exchange": info.get("exchange", "N/A"),
            }
        )

    render_data_header_card("📊 Sector Allocation Breakdown")
    df_sector_pie = pd.DataFrame(
        [{"Sector": r["sector"], "Market Value ($)": r["market_value"]} for r in table_rows]
    )
    fig_sector = px.pie(
        df_sector_pie,
        values="Market Value ($)",
        names="Sector",
        title=f"Portfolio Distribution by Sector ({user_name})",
    )
    st.plotly_chart(
        fig_sector,
        use_container_width=True,
        key=f"portfolio_pie_{uuid.uuid4().hex[:8]}",
    )

    render_data_header_card("📋 Holdings Detail Library & Historical Inspector")
    st.caption(
        "💡 Tip: Click on any **Table Header** to sort by that column. Click again to toggle order. "
        "Click on any **Ticker button** to open its live historical chart."
    )

    sorted_rows, col_widths = render_sortable_table(
        table_id="pf_holdings",
        items=table_rows,
        columns_config=HOLDINGS_COLUMNS,
        sort_key_state="holdings_sort_col",
        sort_asc_state="holdings_sort_asc",
        default_sort="pct_port",
        default_asc=True,
    )

    modal_prefix = "Portfolio Holding Analysis"
    for idx, row in enumerate(sorted_rows, start=1):
        r_cols = st.columns(col_widths)
        ticker = str(row["ticker"])
        gl_val = float(row["gain_loss"])
        gl_color = "#00e676" if gl_val >= 0 else "#ff5252"
        gl_formatted = f"{gl_val:,.2f}" if gl_val >= 0 else f"(${abs(gl_val):,.2f})"

        with r_cols[0]:
            render_table_cell(str(idx), align="center", color="#94a3b8", font_weight="600")
        with r_cols[1]:
            if st.button(
                    f"🔗 {ticker}",
                    key=f"tbl_ticker_{active_user_id}_{ticker}_{idx}",
                    use_container_width=True,
                    help=f"Inspect historical performance for {ticker}",
            ):
                st.session_state[f"modal_period_{ticker}_{modal_prefix}_active"] = "1d"
                open_stock_modal(
                    ticker,
                    holdings_dict,
                    fetch_historical_prices,
                    fetch_live_sector,
                    default_period="1d",
                    modal_title_prefix=modal_prefix,
                )
        with r_cols[2]:
            render_table_cell(str(row["isin"]), monospace=True)
        with r_cols[3]:
            render_table_cell(str(row["name"]), color="#f8fafc", font_weight="500", truncate=True, title=str(row["name"]))
        with r_cols[4]:
            render_table_cell(f"{float(row['shares']):,.4f}", align="right")
        with r_cols[5]:
            render_table_cell(f"{float(row['avg_cost']):,.2f}", align="right")
        with r_cols[6]:
            render_table_cell(f"{float(row['price']):,.2f}", align="right")
        with r_cols[7]:
            render_table_cell(f"{float(row['cost']):,.2f}", align="right")
        with r_cols[8]:
            render_table_cell(f"{float(row['market_value']):,.2f}", align="right")
        with r_cols[9]:
            render_table_cell(f"{float(row['pct_port']):,.2f}%", align="right")
        with r_cols[10]:
            render_table_cell(gl_formatted, align="right", color=gl_color, font_weight="600")
        with r_cols[11]:
            render_table_cell(str(row["sector"]), truncate=True, title=str(row["sector"]))
        with r_cols[12]:
            render_table_cell(str(row["exchange"]), truncate=True, title=str(row["exchange"]))

        render_row_divider()