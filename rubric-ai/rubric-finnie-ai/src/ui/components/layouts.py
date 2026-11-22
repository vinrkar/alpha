import logging
import streamlit as st

from src.tools.chart_tool import create_innovative_market_chart
from src.tools.yfinance_tool import fetch_historical_prices

logger = logging.getLogger(__name__)

PERIOD_OPTIONS: list[tuple[str, str]] = [
    ("1D", "1d"),
    ("5D", "5d"),
    ("1M", "1mo"),
    ("6M", "6mo"),
    ("YTD", "ytd"),
    ("1Y", "1y"),
    ("5Y", "5y"),
    ("ALL", "max"),
]

def _set_modal_period(period_key: str, period_val: str) -> None:
    st.session_state[period_key] = period_val

@st.dialog("📈 Stock Historical Price Inspector", width="large")
def open_stock_modal(
        ticker_sym: str,
        holdings_dict: dict | None = None,
        fetch_cached_historical_prices_func=None,
        fetch_live_sector_func=None,
        default_period: str = "1y",
        modal_title_prefix: str = "Stock Inspector",
) -> None:
    holdings_map = holdings_dict or {}
    holding_info = holdings_map.get(ticker_sym, {})
    asset_name = holding_info.get("name", ticker_sym)
    logger.info("Opening stock inspector modal for %s (%s)", ticker_sym, asset_name)

    period_key = f"modal_period_{ticker_sym}_{modal_title_prefix}_active"
    if period_key not in st.session_state:
        st.session_state[period_key] = default_period

    st.markdown(
        """
        <style>
        [data-testid="stDialog"] div[data-testid="stHorizontalBlock"] > div {
            padding: 0 2px !important;
        }
        [data-testid="stDialog"] button[kind="primary"] {
            background: linear-gradient(135deg, #0ea5e9 0%, #2563eb 100%) !important;
            color: #ffffff !important;
            border: 1px solid rgba(56, 189, 248, 0.8) !important;
            box-shadow: 0 0 12px rgba(14, 165, 233, 0.4) !important;
            font-weight: 700 !important;
            border-radius: 8px !important;
        }
        [data-testid="stDialog"] button[kind="secondary"] {
            background-color: rgba(30, 41, 59, 0.6) !important;
            color: #94a3b8 !important;
            border: 1px solid rgba(255, 255, 255, 0.08) !important;
            font-weight: 600 !important;
            border-radius: 8px !important;
        }
        [data-testid="stDialog"] button[kind="secondary"]:hover {
            background-color: rgba(56, 189, 248, 0.15) !important;
            color: #38bdf8 !important;
            border-color: rgba(56, 189, 248, 0.3) !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(f"### **{ticker_sym}** ({asset_name}) — {modal_title_prefix}")

    isin = holding_info.get("isin", "N/A")
    exchange = holding_info.get("exchange", "N/A")
    sector = holding_info.get("sector", "Other")
    if fetch_live_sector_func:
        try:
            sector = fetch_live_sector_func(ticker_sym)
        except Exception as exc:
            logger.warning("Sector lookup failed for %s: %s", ticker_sym, exc)

    st.caption(f"ISIN: {isin} | Exchange: {exchange} | Sector: {sector}")

    cols = st.columns(len(PERIOD_OPTIONS))
    for idx, (label, period_val) in enumerate(PERIOD_OPTIONS):
        with cols[idx]:
            is_selected = st.session_state[period_key] == period_val
            st.button(
                label,
                key=f"modal_btn_{ticker_sym}_{period_val}_{modal_title_prefix}_{idx}",
                use_container_width=True,
                type="primary" if is_selected else "secondary",
                on_click=_set_modal_period,
                args=(period_key, period_val),
            )

    active_period = st.session_state[period_key]
    status_container = st.empty()
    status_container.markdown(
        f"<div style='color: #38bdf8; font-weight: 600; font-size: 13px; margin: 8px 0;'>"
        f"⏳ Fetching historical data for {ticker_sym} ({active_period.upper()})...</div>",
        unsafe_allow_html=True,
    )

    if fetch_cached_historical_prices_func:
        hist_df = fetch_cached_historical_prices_func(ticker_sym, period=active_period)
    else:
        hist_df = fetch_historical_prices(ticker_sym, period=active_period)

    status_container.empty()

    if hist_df is None or hist_df.empty:
        logger.warning("No historical data found for %s (%s)", ticker_sym, active_period)
        st.warning(f"No historical data found for {ticker_sym} ({active_period}).")
        return

    chart_fig = create_innovative_market_chart(
        hist_df,
        ticker_sym,
        "Area Chart",
        requested_period=active_period,
    )
    st.plotly_chart(
        chart_fig,
        use_container_width=True,
        key=f"modal_chart_{ticker_sym}_{active_period}_{modal_title_prefix}",
    )