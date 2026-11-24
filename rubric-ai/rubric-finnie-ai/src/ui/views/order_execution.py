import logging
import time
from typing import Any

import requests
import streamlit as st

from src.services.market_data_service import (
    fetch_dynamic_trending_tickers,
    fetch_live_market_snapshot_batch,
    fetch_live_sector,
)
from src.tools.yfinance_tool import fetch_historical_prices, fetch_live_market_data
from src.ui.components.layouts import open_stock_modal
from src.ui.components.styles import render_data_header_card
from src.ui.components.tables import (
    render_row_divider,
    render_sortable_table,
    render_table_cell,
)

logger = logging.getLogger(__name__)

TOP_HOLDINGS_COLUMNS: list[dict[str, Any]] = [
    {"key": "ticker", "label": "TICKER", "width": 12},
    {"key": "name", "label": "NAME", "width": 24},
    {"key": "shares", "label": "SHARES", "width": 11},
    {"key": "avg_cost", "label": "AVG. PR", "width": 11},
    {"key": "cost", "label": "COST", "width": 11},
    {"key": "market_value", "label": "MKT VAL", "width": 11},
    {"key": "pct_port", "label": "% PRTF", "width": 12},
]

TRENDING_WATCH_COLUMNS: list[dict[str, Any]] = [
    {"key": "ticker", "label": "TICKER", "width": 11},
    {"key": "name", "label": "NAME", "width": 18},
    {"key": "current_price", "label": "PRICE", "width": 10},
    {"key": "change_pct", "label": "CHANGE", "width": 10},
    {"key": "day_high", "label": "HIGH", "width": 10},
    {"key": "day_low", "label": "LOW", "width": 10},
    {"key": "exchange", "label": "EXCH", "width": 8},
    {"key": "sentiment", "label": "SENT", "width": 9},
]


def _is_staff_or_admin_user(active_user_id: str) -> bool:
    return bool(active_user_id and active_user_id.strip().upper().startswith("R"))


def _can_place_orders(active_user_id: str) -> bool:
    return not _is_staff_or_admin_user(active_user_id)


def _init_order_form_state() -> None:
    st.session_state.setdefault("order_action_select", "BUY")
    st.session_state.setdefault("order_ticker_input", "")
    st.session_state.setdefault("order_shares_input", 0.0)
    st.session_state.setdefault("order_price_input", 0.0)

    if st.session_state.pop("reset_order_form", False):
        st.session_state["order_action_select"] = "BUY"
        st.session_state["order_ticker_input"] = ""
        st.session_state["order_shares_input"] = 0.0
        st.session_state["order_price_input"] = 0.0


def _build_ranked_holdings(holdings: dict[str, Any]) -> list[dict[str, Any]]:
    total_mkt_val = 0.0
    ranked: list[dict[str, Any]] = []

    for ticker, info in holdings.items():
        shares = float(info.get("shares", 0))
        avg_cost = float(info.get("avg_cost", 0.0))
        live_res = fetch_live_market_data(ticker)
        curr_price = (
            float(live_res.get("current_price", avg_cost))
            if isinstance(live_res, dict)
            else avg_cost
        )
        t_cost = shares * avg_cost
        mkt_val = shares * curr_price
        total_mkt_val += mkt_val
        ranked.append(
            {
                "ticker": ticker,
                "name": info.get("name", ticker),
                "shares": shares,
                "avg_cost": avg_cost,
                "cost": t_cost,
                "price": curr_price,
                "market_value": mkt_val,
            }
        )

    for item in ranked:
        item["pct_port"] = (item["market_value"] / total_mkt_val * 100) if total_mkt_val > 0 else 0.0

    return ranked


def _build_trending_watch_records() -> list[dict[str, Any]]:
    dynamic_tickers = fetch_dynamic_trending_tickers()
    if not dynamic_tickers:
        return []

    try:
        df_trend = fetch_live_market_snapshot_batch(dynamic_tickers)
    except Exception as exc:
        logger.warning("Failed to fetch trending watch snapshot: %s", exc)
        return []

    if df_trend is None or df_trend.empty:
        return []

    records: list[dict[str, Any]] = []
    for _, row in df_trend.iterrows():
        curr_price = float(row["current_price"])
        records.append(
            {
                "ticker": str(row["ticker"]),
                "name": str(row.get("name", row["ticker"])),
                "exchange": str(row.get("exchange", "NYSE/NASDAQ")),
                "current_price": curr_price,
                "change_pct": float(row.get("change_pct", 0.0)),
                "day_high": float(row.get("high_52", curr_price * 1.01)),
                "day_low": float(row.get("low_52", curr_price * 0.99)),
                "sentiment": float(row.get("sentiment", 0.0)),
            }
        )
    return records


def _render_new_order_section(
        active_user_id: str,
        selected_admin_target: str | None,
        chat_api_url: str,
) -> None:
    st.markdown("<div style='margin-top: 16px;'></div>", unsafe_allow_html=True)
    render_data_header_card("📝 New Order")

    st.markdown(
        """
        <style>
        input[aria-label="TICKER"] {
            text-transform: uppercase !important;
        }
        div[data-testid="column"] button[kind="primary"] {
            white-space: nowrap !important;
            height: 38px !important;
            margin-top: 24px !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    current_action = st.session_state.get("order_action_select", "BUY")
    est_prefix = "EST. DEBIT (-)" if current_action == "BUY" else "EST. CREDIT (+)"
    est_color = "#ff5252" if current_action == "BUY" else "#00e676"

    with st.container(border=True):
        form_col1, form_col2, form_col3, form_col4, form_col5, form_col6 = st.columns(
            [6, 10, 10, 10, 10, 10],
            gap="medium",
            vertical_alignment="bottom",
        )
        with form_col1:
            trade_action = st.selectbox("ACTION", options=["BUY", "SELL"], key="order_action_select")
        with form_col2:
            ticker_input = (
                st.text_input("TICKER", placeholder="e.g. AAPL", key="order_ticker_input")
                .upper()
                .strip()
            )
        with form_col3:
            shares_input = st.number_input("QTY", min_value=0.0, step=1.0, format="%.4f", key="order_shares_input")
        with form_col4:
            price_input = st.number_input(
                "UNIT PRICE (USD)",
                min_value=0.0,
                step=0.50,
                format="%.2f",
                key="order_price_input",
            )
        with form_col5:
            tx_val = float(shares_input) * float(price_input)
            st.markdown(
                f"""
                <div style="display: flex; flex-direction: column; justify-content: flex-end; align-items: center; text-align: center;">
                    <div class="terminal-field-label" style="height: 18px; line-height: 18px; margin-bottom: 6px;">{est_prefix}</div>
                    <div style="font-size: 18px; font-weight: 700; color: {est_color}; height: 54px; display: flex; align-items: center; justify-content: center;">${tx_val:,.2f}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with form_col6:
            submit_trade = st.button("🚀 Place Order", key="place_order_btn", use_container_width=True, type="primary")

        if submit_trade:
            if not ticker_input:
                st.session_state.order_error_msg = "⚠️ Please specify a valid ticker symbol."
                st.session_state.order_success_msg = None
                st.rerun()
            else:
                target_uid = selected_admin_target if selected_admin_target else active_user_id
                trade_payload = {
                    "user_id": target_uid,
                    "ticker": ticker_input,
                    "action": trade_action,
                    "shares": shares_input,
                    "execution_price": price_input,
                }
                try:
                    trade_api_url = f"{chat_api_url.rsplit('/', 1)[0]}/trade"
                    res = requests.post(trade_api_url, json=trade_payload, timeout=10)
                    if res.status_code == 200:
                        success_msg = res.json().get("message", "Trade processed successfully.")
                        st.session_state.order_success_msg = f"✅ {success_msg}"
                        st.session_state.order_error_msg = None
                        st.session_state.reset_order_form = True
                        st.cache_data.clear()
                        time.sleep(0.5)
                    else:
                        err_detail = res.json().get("detail", res.text)
                        st.session_state.order_error_msg = f"❌ Order Rejected: {err_detail}"
                        st.session_state.order_success_msg = None
                except Exception as exc:
                    st.session_state.order_error_msg = f"❌ Failed to connect to trade gateway: {exc}"
                    st.session_state.order_success_msg = None
                st.rerun()

    if st.session_state.get("order_success_msg"):
        st.markdown("<div style='margin-top: 10px;'></div>", unsafe_allow_html=True)
        sc1, sc2 = st.columns([19, 1], vertical_alignment="center")
        with sc1:
            st.success(st.session_state.order_success_msg)
        with sc2:
            if st.button("✕", key="dismiss_success_btn", help="Dismiss message", use_container_width=True):
                st.session_state.order_success_msg = None
                st.rerun()

    if st.session_state.get("order_error_msg"):
        st.markdown("<div style='margin-top: 10px;'></div>", unsafe_allow_html=True)
        ec1, ec2 = st.columns([19, 1], vertical_alignment="center")
        with ec1:
            st.error(st.session_state.order_error_msg)
        with ec2:
            if st.button("✕", key="dismiss_error_btn", help="Dismiss message", use_container_width=True):
                st.session_state.order_error_msg = None
                st.rerun()


def render_order_execution_tab(
        active_user_id: str,
        active_user_data: dict[str, Any],
        selected_admin_target: str | None,
        chat_api_url: str,
) -> None:
    _init_order_form_state()
    user_holdings = active_user_data.get("holdings", {})
    viewed_investor_id = (
            selected_admin_target
            or active_user_data.get("investor_id")
            or active_user_data.get("user_id")
            or active_user_id
    )

    render_data_header_card("💼 Account Summary")
    st.markdown(
        f"""
        <div style="background-color: rgba(30, 41, 59, 0.6); padding: 14px; border-radius: 10px;
                    border: 1px solid rgba(56, 189, 248, 0.2); margin-bottom: 20px;">
            <div style="display: flex; justify-content: space-between; flex-wrap: wrap; gap: 12px;">
                <div><span style="color: #38bdf8; font-weight: 700;">Active Investor:</span> {active_user_data.get('name', 'N/A')}</div>
                <div><span style="color: #38bdf8; font-weight: 700;">Profile ID:</span> {viewed_investor_id}</div>
                <div><span style="color: #38bdf8; font-weight: 700;">Risk Tolerance:</span> {active_user_data.get('risk_tolerance', 'N/A')}</div>
                <div><span style="color: #38bdf8; font-weight: 700;">Active Holdings:</span> {len(user_holdings)} assets</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    top_col1, top_col2 = st.columns(2, gap="medium")

    with top_col1:
        render_data_header_card("📌 Top Holdings (by Portfolio %)")
        if user_holdings:
            ranked_holdings = _build_ranked_holdings(user_holdings)
            sorted_holdings, h_widths = render_sortable_table(
                table_id="th",
                items=ranked_holdings,
                columns_config=TOP_HOLDINGS_COLUMNS,
                sort_key_state="top_holdings_sort_col",
                sort_asc_state="top_holdings_sort_asc",
                default_sort="pct_port",
                default_asc=False,
                limit=5,
            )
            for idx, row in enumerate(sorted_holdings, start=1):
                rc = st.columns(h_widths)
                ticker = str(row["ticker"])
                with rc[0]:
                    if st.button(
                            f"🔗 {ticker}",
                            key=f"top_hold_{ticker}_{idx}",
                            use_container_width=True,
                            help=f"Inspect live chart for {ticker}",
                    ):
                        open_stock_modal(
                            ticker,
                            user_holdings,
                            fetch_historical_prices,
                            fetch_live_sector,
                            default_period="1d",
                            modal_title_prefix="Top Holdings Analysis",
                        )
                with rc[1]:
                    render_table_cell(str(row["name"]), truncate=True, title=str(row["name"]))
                with rc[2]:
                    render_table_cell(f"{float(row['shares']):,.4f}", align="right")
                with rc[3]:
                    render_table_cell(f"${float(row['avg_cost']):,.2f}", align="right")
                with rc[4]:
                    render_table_cell(f"${float(row['cost']):,.2f}", align="right")
                with rc[5]:
                    render_table_cell(f"${float(row['market_value']):,.2f}", align="right")
                with rc[6]:
                    render_table_cell(f"{float(row['pct_port']):,.2f}%", align="right", color="#38bdf8", font_weight="600")
                render_row_divider()
        else:
            st.info("No holdings currently recorded.")

    with top_col2:
        render_data_header_card("🔥 Top Trending Market Watch (Live US)")
        trending_records = _build_trending_watch_records()
        if not trending_records:
            st.info("No active trending tickers reported by live feed (non-trading hours / weekend).")
        else:
            sorted_trend, t_widths = render_sortable_table(
                table_id="top_mkt",
                items=trending_records,
                columns_config=TRENDING_WATCH_COLUMNS,
                sort_key_state="top_market_sort_col",
                sort_asc_state="top_market_sort_asc",
                default_sort="sentiment",
                default_asc=False,
                limit=5,
            )
            for idx, row in enumerate(sorted_trend, start=1):
                chg = float(row["change_pct"])
                chg_color = "#00e676" if chg >= 0 else "#ff5252"
                chg_str = f"+{chg:,.2f}%" if chg >= 0 else f"{chg:,.2f}%"
                ticker = str(row["ticker"])
                exch = str(row["exchange"])

                rc = st.columns(t_widths)
                with rc[0]:
                    if st.button(
                            f"🔗 {ticker}",
                            key=f"sort_top_trend_{ticker}_{idx}",
                            use_container_width=True,
                            help=f"Inspect live chart for {ticker}",
                    ):
                        open_stock_modal(
                            ticker,
                            {},
                            fetch_historical_prices,
                            fetch_live_sector,
                            default_period="1d",
                            modal_title_prefix="Market Watch Inspector",
                        )
                with rc[1]:
                    render_table_cell(str(row["name"]), truncate=True, title=str(row["name"]))
                with rc[2]:
                    render_table_cell(f"${float(row['current_price']):,.2f}", align="right")
                with rc[3]:
                    render_table_cell(chg_str, align="right", color=chg_color, font_weight="600")
                with rc[4]:
                    render_table_cell(f"${float(row['day_high']):,.2f}", align="right")
                with rc[5]:
                    render_table_cell(f"${float(row['day_low']):,.2f}", align="right")
                with rc[6]:
                    render_table_cell(exch, align="right", color="#38bdf8", font_weight="600", title=exch)
                with rc[7]:
                    render_table_cell(f"{float(row['sentiment']):,.2f}", align="right", color="#38bdf8")
                render_row_divider()

    if _can_place_orders(active_user_id):
        _render_new_order_section(active_user_id, selected_admin_target, chat_api_url)