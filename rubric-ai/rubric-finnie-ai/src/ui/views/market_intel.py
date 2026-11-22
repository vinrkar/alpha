from datetime import date, timedelta
import logging
from typing import Any

import pandas as pd
import streamlit as st

from src.services.market_data_service import (
    fetch_dynamic_trending_tickers,
    fetch_live_market_snapshot_batch,
    fetch_live_sector,
)
from src.tools.chart_tool import create_innovative_market_chart
from src.tools.yfinance_tool import fetch_historical_prices
from src.ui.components.layouts import open_stock_modal
from src.ui.components.styles import render_data_header_card, render_subheader_card
from src.ui.components.tables import (
    render_row_divider,
    render_sortable_table,
    render_table_cell,
)

logger = logging.getLogger(__name__)

MARKET_COLUMNS: list[dict[str, Any]] = [
    {"key": "idx", "label": "#", "width": 0.5},
    {"key": "ticker", "label": "TICKER", "width": 1.2},
    {"key": "current_price", "label": "PRICE ($)", "width": 1.2},
    {"key": "change_pct", "label": "CHANGE (%)", "width": 1.4},
    {"key": "volume_raw", "label": "VOLUME", "width": 1.2},
    {"key": "market_cap_raw", "label": "MKT CAP", "width": 1.4},
    {"key": "pe_ratio", "label": "P/E", "width": 1.0},
    {"key": "eps", "label": "EPS", "width": 1.0},
    {"key": "high_52", "label": "52W HIGH", "width": 1.2},
    {"key": "low_52", "label": "52W LOW", "width": 1.2},
    {"key": "dividend", "label": "DIV.", "width": 1.1},
    {"key": "ex_dividend", "label": "EX-DIV", "width": 1.2},
    {"key": "rsi", "label": "RSI", "width": 1.0},
    {"key": "macd", "label": "MACD", "width": 1.2},
    {"key": "exchange", "label": "EXCH", "width": 1.0},
    {"key": "sentiment", "label": "SENTIMENT", "width": 1.4},
]

@st.cache_data(ttl=60, show_spinner=False)
def _cached_market_snapshot(tickers_tuple: tuple[str, ...]) -> pd.DataFrame:
    return fetch_live_market_snapshot_batch(list(tickers_tuple))

@st.fragment
def render_market_chart_section(default_ticker: str) -> None:
    today_dt = date.today()

    st.session_state.setdefault("analyzer_ticker_input", default_ticker)
    st.session_state.setdefault("analyzer_chart_type", "Area Chart")
    st.session_state.setdefault("analyzer_start_date", today_dt - timedelta(days=365))
    st.session_state.setdefault("analyzer_end_date", today_dt)
    st.session_state.setdefault("rendered_ticker", default_ticker)
    st.session_state.setdefault("rendered_chart_type", "Area Chart")

    with st.form(key="market_chart_form", border=False):
        col_h1, col_h2, col_h3, col_h4, col_h5 = st.columns(
            [2.0, 1.8, 1.8, 1.8, 1.5],
            gap="medium",
            vertical_alignment="bottom",
        )
        with col_h1:
            input_ticker = (
                st.text_input(
                    "TICKER",
                    value=st.session_state.analyzer_ticker_input,
                    key="widget_ticker_input",
                )
                .upper()
                .strip()
            )
            st.session_state.analyzer_ticker_input = input_ticker
        with col_h2:
            st.selectbox(
                "CHART TYPE",
                options=["Area Chart", "Line Chart", "Candlestick"],
                key="analyzer_chart_type",
            )
        with col_h3:
            st.date_input("START DATE", max_value=today_dt, key="analyzer_start_date")
        with col_h4:
            st.date_input("END DATE", max_value=today_dt, key="analyzer_end_date")
        with col_h5:
            st.markdown("<div style='height: 2px;'></div>", unsafe_allow_html=True)
            fetch_clicked = st.form_submit_button(
                "📊 Fetch & Render",
                use_container_width=True,
                type="primary",
            )

    if fetch_clicked or "active_chart_fig" not in st.session_state:
        active_t = st.session_state.analyzer_ticker_input
        active_c = st.session_state.analyzer_chart_type
        active_s = st.session_state.analyzer_start_date
        active_e = st.session_state.analyzer_end_date

        if not active_t:
            st.warning("⚠️ Please enter a valid ticker to analyze.")
            st.session_state.active_chart_fig = None
        elif active_s > active_e:
            st.warning("⚠️ **Invalid Date Range:** Start Date cannot be later than End Date.")
            st.session_state.active_chart_fig = None
        else:
            fetch_interval = "5m" if active_s == active_e else "1d"
            query_end = active_e + timedelta(days=1)

            status_container = st.empty()
            status_container.markdown(
                f"<div style='color: #38bdf8; font-weight: 600; font-size: 13px; margin: 8px 0;'>"
                f"⏳ Fetching market data for {active_t}...</div>",
                unsafe_allow_html=True,
            )

            hist_df = fetch_historical_prices(
                active_t,
                start=str(active_s),
                end=str(query_end),
                interval=fetch_interval,
            )
            status_container.empty()

            if hist_df.empty:
                st.warning(f"⚠️ No historical price data found for ticker '{active_t}'.")
                st.session_state.active_chart_fig = None
            else:
                st.session_state.active_chart_fig = create_innovative_market_chart(
                    hist_df, active_t, active_c
                )
                st.session_state.rendered_ticker = active_t
                st.session_state.rendered_chart_type = active_c

    if st.session_state.get("active_chart_fig"):
        st.plotly_chart(
            st.session_state.active_chart_fig,
            use_container_width=True,
            key=f"market_chart_{st.session_state.rendered_ticker}_{st.session_state.rendered_chart_type}",
        )

def render_market_intelligence_tab(active_user_data: dict[str, Any]) -> None:
    render_subheader_card(
        "📡 Real-Time Market Data & Technical Indicators",
        subtitle="Live dynamic trending stocks fetched in real-time via yfinance.",
    )

    trending_tickers = fetch_dynamic_trending_tickers()

    loading_placeholder = st.empty()
    loading_placeholder.markdown(
        "<div style='color: #38bdf8; font-weight: 600; font-size: 13px; margin: 8px 0;'>"
        "⏳ Connecting to real-time market feeds (NYSE / NASDAQ)...</div>",
        unsafe_allow_html=True,
    )
    df_market_raw = (
        _cached_market_snapshot(tuple(trending_tickers)) if trending_tickers else pd.DataFrame()
    )
    loading_placeholder.empty()

    render_data_header_card("🔥 Top Trending Market Intelligence (Live US)")
    st.caption(
        "💡 Tip: Click on any **Table Header** to sort by that column. "
        "Click on any **Ticker button** to open its live historical chart."
    )

    default_chart_ticker = "SPY"
    if df_market_raw.empty:
        st.info(
            "No active trending equities reported by live market feed at the moment "
            "(weekend / non-trading hours)."
        )
    else:
        records = df_market_raw.to_dict(orient="records")
        sorted_records, col_widths = render_sortable_table(
            table_id="mkt",
            items=records,
            columns_config=MARKET_COLUMNS,
            sort_key_state="market_sort_col",
            sort_asc_state="market_sort_asc",
            default_sort="sentiment",
            default_asc=True,
        )

        for idx, row in enumerate(sorted_records, start=1):
            r_cols = st.columns(col_widths)
            ticker = str(row["ticker"])
            chg = float(row.get("change_pct", 0.0))
            chg_color = "#00e676" if chg >= 0 else "#ff5252"
            chg_text = f"{'+' if chg >= 0 else ''}{chg:,.2f}%"

            with r_cols[0]:
                render_table_cell(str(idx), color="#94a3b8", font_weight="600")
            with r_cols[1]:
                if st.button(f"🔗 {ticker}", key=f"mkt_ticker_{ticker}_{idx}", use_container_width=True):
                    open_stock_modal(
                        ticker,
                        {},
                        fetch_historical_prices,
                        fetch_live_sector,
                        default_period="1d",
                        modal_title_prefix="Market Intelligence Inspector",
                    )
            with r_cols[2]:
                render_table_cell(f"{float(row['current_price']):,.2f}", align="right")
            with r_cols[3]:
                render_table_cell(chg_text, align="right", color=chg_color, font_weight="600")
            with r_cols[4]:
                render_table_cell(str(row.get("volume_str", "")), align="right")
            with r_cols[5]:
                render_table_cell(str(row.get("market_cap_str", "")), align="right")
            with r_cols[6]:
                render_table_cell(str(row.get("pe_ratio", "")), align="right")
            with r_cols[7]:
                render_table_cell(str(row.get("eps", "")), align="right")
            with r_cols[8]:
                render_table_cell(f"{float(row.get('high_52', 0.0)):,.2f}", align="right")
            with r_cols[9]:
                render_table_cell(f"{float(row.get('low_52', 0.0)):,.2f}", align="right")
            with r_cols[10]:
                render_table_cell(str(row.get("dividend", "")), align="right")
            with r_cols[11]:
                render_table_cell(str(row.get("ex_dividend", "")), align="right")
            with r_cols[12]:
                render_table_cell(f"{float(row.get('rsi', 0.0)):,.2f}", align="right")
            with r_cols[13]:
                render_table_cell(str(row.get("macd", "")), align="right", color="#00e676", font_weight="600")
            with r_cols[14]:
                exch = str(row.get("exchange", ""))
                render_table_cell(exch, align="right", color="#38bdf8", font_weight="600", title=exch)
            with r_cols[15]:
                render_table_cell(f"{float(row.get('sentiment', 0.0)):,.2f}", align="right", color="#38bdf8")

            render_row_divider()

        default_chart_ticker = str(sorted_records[0]["ticker"]) if sorted_records else "SPY"

    st.markdown("<div style='margin-top: 16px;'></div>", unsafe_allow_html=True)
    render_data_header_card("📈 Interactive Historical Price & Chart Analyzer")
    render_market_chart_section(default_chart_ticker)