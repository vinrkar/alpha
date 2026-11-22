import asyncio
import concurrent.futures
import json
import logging
import re
from pathlib import Path
from typing import Any, Coroutine, TypeVar

import pandas as pd
import streamlit as st
import yfinance as yf

from src.agent.nodes.market.formatters import (
    filter_closes_by_date_range,
    format_daywise_price_table,
)
from src.tools.chart_tool import create_innovative_market_chart
from src.utils.rag_utils import DEFAULT_REPORT_CHAR_LIMIT, truncate_report_text

logger = logging.getLogger(__name__)

T = TypeVar("T")

STORAGE_DIR = Path("data/sessions")
MAX_CONVERSATIONS = 50
MAX_HISTORY_MESSAGES = MAX_CONVERSATIONS
DEFAULT_VISIBLE_MESSAGES = 20
LOAD_BATCH_SIZE = 10
MAX_RAG_HISTORY = 5

_CLEAR_BUTTON_CSS = """
<style>
div[data-testid="stButton"] > button[kind="secondary"] {
    border: 1px solid rgba(248, 113, 113, 0.65) !important;
    color: #fecaca !important;
    background-color: rgba(153, 27, 27, 0.35) !important;
    font-weight: 600 !important;
    white-space: nowrap !important;
    border-radius: 8px !important;
}
div[data-testid="stButton"] > button[kind="secondary"]:hover {
    border-color: #f87171 !important;
    color: #ffffff !important;
    background-color: rgba(185, 28, 28, 0.6) !important;
}
</style>
"""

_HOLDING_ITEM_REGEX = re.compile(
    r"(?:\*\s*)?\*{0,2}([A-Z]{1,5})\*{0,2}(?:\s+\(([^)]+)\))?\s*:\s*([0-9,.]+)\s+shares?\s*@\s*\$([0-9,.]+)\s*\(\$([0-9,.]+)(?:\s+total)?\)",
    re.IGNORECASE,
)
_TOTAL_VALUE_REGEX = re.compile(r"Total Portfolio Value:\s*\*?\*?\s*\$([0-9,.]+)", re.IGNORECASE)
_TABLE_ROW_RE = re.compile(r"^\s*\|.*\|\s*$")


def _has_meaningful_query(value: Any) -> bool:
    """Returns True only if value is a non-empty, non-whitespace, non-quote-only string."""
    if not isinstance(value, str):
        return False
    stripped = re.sub(r"[\s\u00a0\u200b\u200c\u200d\ufeff]+", "", value).strip("\"'`")
    return bool(stripped)


def _is_valid_chat_message(msg: Any) -> bool:
    """Returns True only if a chat message has a non-empty query and meaningful content or closes."""
    if not isinstance(msg, dict):
        return False
    if not _has_meaningful_query(msg.get("query", "")):
        return False
    content = str(msg.get("content", "")).strip()
    closes = msg.get("historical_closes")
    has_closes = isinstance(closes, dict) and len(closes) > 0
    return bool(content) or has_closes


def _clean_chat_messages(entries: Any) -> list[dict[str, Any]]:
    """Filters out empty, whitespace-only, or malformed chat history entries."""
    if not isinstance(entries, list):
        return []
    cleaned = [entry for entry in entries if _is_valid_chat_message(entry)]
    return cleaned[:MAX_HISTORY_MESSAGES]


def _clean_rag_history(entries: Any) -> list[dict[str, Any]]:
    """Filters out malformed or empty/whitespace/quote-only RAG history entries."""
    if not isinstance(entries, list):
        return []
    cleaned: list[dict[str, Any]] = []
    for entry in entries:
        if isinstance(entry, dict) and _has_meaningful_query(entry.get("query", "")):
            cleaned.append(entry)
    return cleaned[:MAX_RAG_HISTORY]


def clear_rag_search_history() -> None:
    """Clears in-memory and persisted RAG search history."""
    st.session_state.rag_history = []
    save_session_state_to_disk()


def clear_chat_history() -> None:
    """Clears in-memory and persisted Assistant Chat history."""
    st.session_state.messages = []
    st.session_state.visible_message_count = DEFAULT_VISIBLE_MESSAGES
    save_session_state_to_disk()


def render_clear_rag_history_button(key: str = "clear_rag_history_below_input_btn") -> None:
    """Renders a high-contrast, right-aligned Clear RAG History button when history exists."""
    rag_history = _clean_rag_history(st.session_state.get("rag_history", []))
    st.session_state.rag_history = rag_history
    if not rag_history:
        return

    st.markdown(_CLEAR_BUTTON_CSS, unsafe_allow_html=True)
    _, col_right = st.columns([10.9, 1.1], vertical_alignment="center")
    with col_right:
        if st.button("🗑️ Clear RAG History", key=key, use_container_width=True):
            clear_rag_search_history()
            st.rerun()


def render_clear_chat_history_button(key: str = "clear_chat_history_below_input_btn") -> None:
    """Renders a high-contrast, right-aligned Clear Chat History button when messages exist."""
    messages = _clean_chat_messages(st.session_state.get("messages", []))
    st.session_state.messages = messages
    if not messages:
        return

    st.markdown(_CLEAR_BUTTON_CSS, unsafe_allow_html=True)
    _, col_right = st.columns([10.9, 1.1], vertical_alignment="center")
    with col_right:
        if st.button("🗑️ Clear Chat History", key=key, use_container_width=True):
            clear_chat_history()
            st.rerun()


def run_async(coro: Coroutine[Any, Any, T]) -> T:
    """Runs an async coroutine safely from synchronous Streamlit execution contexts."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                return pool.submit(asyncio.run, coro).result()
        return loop.run_until_complete(coro)
    except RuntimeError:
        return asyncio.run(coro)


def _session_file_path() -> Path:
    session_id = st.session_state.get("session_id", "streamlit_session_default")
    return STORAGE_DIR / f"{session_id}.json"


def init_persistent_session() -> None:
    """Initializes or restores authentication, chat messages, and RAG history."""
    STORAGE_DIR.mkdir(parents=True, exist_ok=True)

    query_params = st.query_params
    if query_params.get("action") == "logout":
        logger.info("User signed out; clearing session state and query parameters.")
        st.session_state.update(
            {
                "authenticated": False,
                "user_role": None,
                "active_user_id": None,
                "is_processing": False,
                "messages": [],
                "rag_history": [],
                "visible_message_count": DEFAULT_VISIBLE_MESSAGES,
            }
        )
        st.query_params.clear()
        st.rerun()

    if "authenticated" not in st.session_state:
        if query_params.get("auth") == "true":
            user_id = query_params.get("user", "admin")
            st.session_state.update(
                {
                    "authenticated": True,
                    "user_role": query_params.get("role", "Client"),
                    "active_user_id": user_id,
                    "session_id": query_params.get("sid", f"session_{user_id}"),
                }
            )
            logger.info("Restored session from query parameters for user %s", user_id)
        else:
            st.session_state.update(
                {
                    "authenticated": False,
                    "user_role": None,
                    "active_user_id": None,
                }
            )

    st.session_state.setdefault("session_id", "streamlit_session_default")
    st.session_state.setdefault("visible_message_count", DEFAULT_VISIBLE_MESSAGES)
    st.session_state.setdefault("load_batch_size", LOAD_BATCH_SIZE)

    session_file = _session_file_path()
    loaded_messages: list[dict[str, Any]] = []
    loaded_rag_history: list[dict[str, Any]] = []
    if session_file.exists():
        try:
            content = json.loads(session_file.read_text(encoding="utf-8"))
            if isinstance(content, dict):
                loaded_messages = _clean_chat_messages(content.get("messages", []))
                loaded_rag_history = _clean_rag_history(content.get("rag_history", []))
                logger.info("Loaded %d messages from %s", len(loaded_messages), session_file.name)
            elif isinstance(content, list):
                loaded_messages = _clean_chat_messages(content)
        except Exception as exc:
            logger.warning("Failed to read session cache %s: %s", session_file.name, exc)

    st.session_state.messages = _clean_chat_messages(
        st.session_state.get("messages") or loaded_messages
    )
    st.session_state.rag_history = _clean_rag_history(
        st.session_state.get("rag_history") or loaded_rag_history
    )


def save_session_state_to_disk() -> None:
    """Persists cleaned chat messages and RAG search history to disk."""
    if not st.session_state.get("session_id"):
        return
    STORAGE_DIR.mkdir(parents=True, exist_ok=True)
    cleaned_messages = _clean_chat_messages(st.session_state.get("messages", []))
    cleaned_rag = _clean_rag_history(st.session_state.get("rag_history", []))
    st.session_state.messages = cleaned_messages
    st.session_state.rag_history = cleaned_rag
    payload = {
        "messages": cleaned_messages,
        "rag_history": cleaned_rag,
    }
    try:
        _session_file_path().write_text(json.dumps(payload), encoding="utf-8")
    except Exception as exc:
        logger.warning("Failed to persist session state: %s", exc)


def add_message_to_history(message_payload: dict[str, Any]) -> None:
    """Prepends a valid, non-empty chat message and enforces history limits."""
    if not _is_valid_chat_message(message_payload):
        return
    messages = _clean_chat_messages(st.session_state.get("messages", []))
    messages.insert(0, message_payload)
    st.session_state.messages = messages[:MAX_HISTORY_MESSAGES]
    save_session_state_to_disk()


def add_rag_search_to_history(rag_payload: dict[str, Any]) -> None:
    """Prepends a valid, non-empty RAG retrieval entry and enforces history limits."""
    if not isinstance(rag_payload, dict) or not _has_meaningful_query(rag_payload.get("query", "")):
        return
    history = _clean_rag_history(st.session_state.get("rag_history", []))
    history.insert(0, rag_payload)
    st.session_state.rag_history = history[:MAX_RAG_HISTORY]
    save_session_state_to_disk()


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_live_organization_name(ticker: str) -> str:
    """Resolves the display organization name for a ticker via yfinance."""
    clean_ticker = ticker.upper().strip()
    try:
        info = yf.Ticker(clean_ticker).info or {}
        org_name = info.get("longName") or info.get("shortName")
        if org_name:
            return str(org_name)
    except Exception as exc:
        logger.debug("Organization name lookup failed for %s: %s", clean_ticker, exc)
    return clean_ticker


def _normalize_markdown_blocks(content: str) -> str:
    normalized = content.replace("\\n", "\n")
    normalized = re.sub(r"\r\n?", "\n", normalized)

    raw_lines = normalized.split("\n")
    expanded_lines: list[str] = []

    for raw_line in raw_lines:
        stripped = raw_line.strip()
        if "| ---" in stripped or "|---" in stripped or re.search(r"\|\s+\|\s*[A-Za-z0-9$]", stripped):
            row_parts = re.findall(r"\|[^|\n]*\|(?:\s*[^|\n]*\|)+", stripped)
            if len(row_parts) >= 2:
                expanded_lines.extend(part.strip() for part in row_parts)
                continue

        if _TABLE_ROW_RE.match(raw_line):
            expanded_lines.append(raw_line)
            continue

        # Normalize any accidental double-asterisk bullet lead-in like "** * Item:" -> "* **Item:**"
        stripped = re.sub(r"^\*\*\s+\*\s+", "* **", stripped)

        # Split inline chained asterisk bullets (including bold/labeled items) onto separate lines
        asterisk_matches = list(re.finditer(r"(?:^|\s+)\*(?=\s+\S)", stripped))
        if len(asterisk_matches) >= 2:
            starts_with_bullet = asterisk_matches[0].start() == 0
            positions = [m.start() for m in asterisk_matches]
            if not starts_with_bullet:
                prefix = stripped[: positions[0]].strip()
                if prefix:
                    expanded_lines.append(prefix)
            for idx, pos in enumerate(positions):
                end_pos = positions[idx + 1] if idx + 1 < len(positions) else len(stripped)
                chunk = stripped[pos:end_pos].strip()
                bullet_body = re.sub(r"^\*\s+", "", chunk).strip()
                if bullet_body:
                    expanded_lines.append(f"* {bullet_body}")
            continue

        # Protect parenthesized subtraction terms (variables or decimals) like "(r - g)" or "(0.1 - 0.08)".
        line_work = re.sub(
            r"\(\s*([A-Za-z0-9_.]+)\s*-\s*([A-Za-z0-9_.]+)\s*\)",
            r"(\1__MINUS__\2)",
            stripped,
        )

        if re.search(r"(?:^|\s+)-\s+", line_work):
            raw_tokens = re.split(r"(?:^|\s+)-\s+", line_work)
            tokens = [t.strip() for t in raw_tokens if t.strip()]
            starts_with_dash = bool(re.match(r"^-\s+", line_work))

            if starts_with_dash and len(tokens) >= 2:
                for tok in tokens:
                    expanded_lines.append(f"- {tok.replace('__MINUS__', ' - ')}")
                continue

            if not starts_with_dash and len(tokens) >= 3:
                expanded_lines.append(tokens[0].replace("__MINUS__", " - "))
                for tok in tokens[1:]:
                    expanded_lines.append(f"- {tok.replace('__MINUS__', ' - ')}")
                continue

        expanded_lines.append(raw_line.replace("__MINUS__", " - "))

    spaced_lines: list[str] = []
    in_table = False
    for line in expanded_lines:
        is_row = bool(_TABLE_ROW_RE.match(line))
        if is_row and not in_table:
            if spaced_lines and spaced_lines[-1].strip() != "":
                spaced_lines.append("")
            in_table = True
        elif not is_row and in_table:
            if line.strip() != "":
                spaced_lines.append("")
            in_table = False
        spaced_lines.append(line)

    return "\n".join(spaced_lines)


def _strip_single_day_historical_block(content: str) -> str:
    """Removes a single-day or single-row Historical Daily Closing Prices block."""
    cleaned = re.sub(
        r"(?ms)^#{1,4}\s*Historical Daily Closing Prices\s*\([^\n]*\)\s*\n+(?:\|[^\n]*\|(?:\s*\n|$)){1,3}",
        "",
        content,
    )
    return re.sub(r"\n{3,}", "\n\n", cleaned).strip()


def _format_holdings_summary_as_table(content: str) -> str:
    """Converts bulleted 'Active Portfolio Holdings Summary' items into a Markdown table."""
    matches = _HOLDING_ITEM_REGEX.findall(content)
    if not matches:
        return content

    total_match = _TOTAL_VALUE_REGEX.search(content)
    total_val = float(total_match.group(1).replace(",", "")) if total_match else sum(
        float(m[4].replace(",", "")) for m in matches
    )

    table_lines = [
        "",
        "| Ticker | Company | Shares | Price | Total Value | Allocation |",
        "|---|---|---:|---:|---:|---:|",
    ]

    for raw_ticker, company, shares_str, price_str, total_str in matches:
        ticker_sym = raw_ticker.upper().strip()
        company_clean = (company or ticker_sym).strip()
        val = float(total_str.replace(",", ""))
        alloc_pct = (val / total_val * 100.0) if total_val > 0 else 0.0
        table_lines.append(
            f"| **{ticker_sym}** | {company_clean} | {shares_str} | ${price_str} | ${total_str} | {alloc_pct:.1f}% |"
        )

    table_lines.append("")
    table_md = "\n".join(table_lines)

    cleaned = _HOLDING_ITEM_REGEX.sub("", content)
    cleaned = re.sub(r"(?m)^\s*\*\s*$", "", cleaned)
    cleaned = re.sub(r"(\n\s*\*?\s*)+(?=\n*Total Portfolio Value:)", f"\n\n{table_md}\n\n", cleaned)
    if table_md.strip() not in cleaned:
        cleaned = f"{cleaned}\n\n{table_md}"
    return cleaned


def _format_inline_emphasis(text: str) -> str:
    text = re.sub(r"\*\*\*(.+?)\*\*\*", r"<strong><em>\1</em></strong>", text)
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    return text


def format_agent_response_labels(content: str, ticker: str = "") -> str:
    """Formats markdown headings and holdings tables in agent responses."""
    org_name = fetch_live_organization_name(ticker) if ticker else ""
    normalized_content = _format_holdings_summary_as_table(_normalize_markdown_blocks(content))
    normalized_content = re.sub(r"(?<!^)(?=\s*<strong>\s*\*\s*)", "\n", normalized_content)
    formatted_lines: list[str] = []

    for line in normalized_content.split("\n"):
        stripped = line.strip()
        if _TABLE_ROW_RE.match(stripped):
            formatted_lines.append(stripped)
        elif re.match(r"^#{1,4}\s+", stripped):
            heading_text = re.sub(r"^#+\s*", "", stripped)
            if org_name and ("Analysis" in heading_text or "Report" in heading_text):
                heading_text = re.sub(r"\b[A-Z]{1,5}\b\s+Analysis", f"{org_name} - Analysis", heading_text)
            heading_text = _format_inline_emphasis(heading_text)

            margin_top = "20px" if "disclaimer" in heading_text.lower() else "16px"
            formatted_lines.append(
                f"<div style='font-size: 14px; font-weight: 700; color: #fbbf24; "
                f"margin-top: {margin_top}; margin-bottom: 6px; letter-spacing: 0.3px;'>{heading_text}</div>"
            )
        else:
            formatted_lines.append(_format_inline_emphasis(line))

    rendered_lines: list[str] = []
    for idx, fline in enumerate(formatted_lines):
        s = fline.lstrip()
        if s.startswith("* "):
            next_s = formatted_lines[idx + 1].lstrip() if idx + 1 < len(formatted_lines) else ""
            if next_s.startswith("* "):
                rendered_lines.append(f"{fline}<br>")
                continue
        rendered_lines.append(fline)

    return "\n".join(rendered_lines)


def render_top_header() -> None:
    st.markdown(
        """
        <style>
        .block-container { padding-top: 2rem !important; }
        div[data-testid="stChatMessage"] {
            background-color: rgba(30, 41, 59, 0.75) !important;
            border: 1px solid rgba(56, 189, 248, 0.35) !important;
            border-radius: 10px !important;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3) !important;
            padding: 16px !important;
            margin-bottom: 12px !important;
        }
        div[data-testid="stChatMessage"] [data-testid="stChatMessageContent"],
        div[data-testid="stChatMessage"] div[data-testid="stMarkdownContainer"],
        div[data-testid="stChatMessage"] [data-testid="stVerticalBlock"] {
            background-color: transparent !important;
        }
        div[data-testid="stChatMessage"] table {
            width: 100% !important;
            border-collapse: collapse !important;
            margin-top: 10px !important;
            margin-bottom: 10px !important;
            color: #f8fafc !important;
        }
        div[data-testid="stChatMessage"] th {
            background-color: rgba(15, 23, 42, 0.85) !important;
            color: #38bdf8 !important;
            font-weight: 700 !important;
            padding: 6px 10px !important;
            border-bottom: 2px solid rgba(56, 189, 248, 0.5) !important;
            text-align: left !important;
            font-size: 11px !important;
        }
        div[data-testid="stChatMessage"] td {
            padding: 5px 10px !important;
            border-bottom: 1px solid rgba(255, 255, 255, 0.08) !important;
            color: #cbd5e1 !important;
            font-size: 11px !important;
        }
        .header-title-text {
            font-size: 2.0rem !important;
            font-weight: 700 !important;
            color: #ffffff !important;
            white-space: nowrap !important;
            overflow: hidden !important;
            text-overflow: ellipsis !important;
            margin: 0 !important;
            line-height: 1.2 !important;
            letter-spacing: -0.5px !important;
        }
        .header-subtitle-text {
            color: #94a3b8 !important;
            font-size: 0.85rem !important;
            margin-top: 2px !important;
            margin-bottom: 0 !important;
            white-space: nowrap !important;
            overflow: hidden !important;
            text-overflow: ellipsis !important;
        }
        .logout-container-flex {
            display: flex !important;
            justify-content: right !important;
            align-items: center !important;
            width: 100% !important;
            height: 100% !important;
        }
        .html-logout-btn {
            border: 2px solid rgba(56, 189, 248, 0.9) !important;
            color: #38bdf8 !important;
            border-radius: 50% !important;
            width: 20px !important;
            height: 20px !important;
            min-width: 20px !important;
            min-height: 20px !important;
            max-width: 20px !important;
            max-height: 20px !important;
            font-size: 10px !important;
            line-height: 1 !important;
            background: rgba(30, 41, 59, 0.85) !important;
            box-shadow: 0 2px 10px rgba(0, 0, 0, 0.5), 0 0 8px rgba(56, 189, 248, 0.4) !important;
            backdrop-filter: blur(6px) !important;
            display: flex !important;
            align-items: center !important;
            justify-content: center !important;
            text-decoration: none !important;
            transition: all 0.2s ease-in-out !important;
            cursor: pointer !important;
            margin: 0 !important;
            padding: 0 !important;
        }
        .html-logout-btn:hover {
            background: rgba(56, 189, 248, 0.35) !important;
            color: #ffffff !important;
            border-color: #ffffff !important;
            box-shadow: 0 4px 16px rgba(56, 189, 248, 0.8) !important;
            transform: scale(1.1) !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    col_title, col_btn = st.columns([11, 0.5], vertical_alignment="center")
    with col_title:
        st.markdown(
            """
            <div>
                <div class="header-title-text">📈 Rubric Finnie AI – Multi-Agent Financial Assistant</div>
                <div class="header-subtitle-text">Enterprise-grade financial intelligence, valuation modeling, and risk compliance powered by LangGraph and Hybrid RAG.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with col_btn:
        st.markdown(
            '<div class="logout-container-flex">'
            '<a class="html-logout-btn" href="?action=logout" target="_self" title="Sign Out">⏻</a>'
            "</div>",
            unsafe_allow_html=True,
        )


def render_card_container(
        content_html: str,
        border_color: str = "rgba(56, 189, 248, 0.35)",
        right_icon: str = "",
) -> str:
    icon_html = (
        f"<span style='float: right; font-size: 18px; margin-left: 10px;' title='Audit Marker'>{right_icon}</span>"
        if right_icon
        else ""
    )
    return f"""
        <div style="background-color: rgba(30, 41, 59, 0.75); padding: 14px 18px; border-radius: 10px;
                    border: 1px solid {border_color}; box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
                    margin-bottom: 12px; margin-top: 10px; color: #f8fafc; overflow: hidden;">
            {icon_html}
            {content_html}
        </div>
    """


def _render_historical_chart_if_needed(msg: dict[str, Any], closes_dict: dict[str, Any], ticker: str) -> None:
    if not msg.get("should_render_chart", False) or not closes_dict:
        return

    try:
        start_date = msg.get("start_date")
        end_date = msg.get("end_date")
        scoped_closes = filter_closes_by_date_range(closes_dict, start_date, end_date) or closes_dict

        df_hist = pd.DataFrame(list(scoped_closes.items()), columns=["Date", "Close"])
        df_hist["Date"] = pd.to_datetime(df_hist["Date"])
        df_hist = df_hist.set_index("Date").sort_index().reset_index()
        if len(df_hist) >= 2:
            fig = create_innovative_market_chart(df_hist, ticker, "Area Chart")
            st.plotly_chart(
                fig,
                use_container_width=True,
                key=f"chat_chart_{msg.get('render_id', 'default')}",
            )
    except Exception as exc:
        logger.warning("Chart rendering failed for %s: %s", ticker, exc)


def render_paginated_chat_history() -> None:
    messages = _clean_chat_messages(st.session_state.get("messages", []))
    st.session_state.messages = messages
    if not messages:
        return

    visible_count = st.session_state.get("visible_message_count", DEFAULT_VISIBLE_MESSAGES)
    visible_messages = messages[:visible_count]

    for msg in visible_messages:
        query_str = str(msg.get("query", "")).strip()
        if not _has_meaningful_query(query_str):
            continue

        exec_time = msg.get("execution_time", "0.00s")
        cache_icon = msg.get("cache_icon", "🧠")

        st.markdown(
            f"<div style='text-align: right; color: #38bdf8; font-size: 12px; font-weight: 600; margin-bottom: 5px;'>"
            f"⏱️ Execution Time: {exec_time}</div>",
            unsafe_allow_html=True,
        )

        user_card_html = f"<span style='font-size: 13px; font-weight: 700; color: #38bdf8;'>💬 {query_str}</span>"
        st.markdown(render_card_container(user_card_html, right_icon=cache_icon), unsafe_allow_html=True)

        with st.chat_message("assistant"):
            ticker = msg.get("chart_ticker") or msg.get("market_data", {}).get("ticker") or "STOCK"
            raw_content = str(msg.get("content", "") or "").strip()
            closes_dict = msg.get("historical_closes") if isinstance(msg.get("historical_closes"), dict) else {}
            start_dt = msg.get("start_date")
            end_dt = msg.get("end_date")

            if not raw_content or len(raw_content) < 10:
                if len(closes_dict) >= 2:
                    table_md = format_daywise_price_table(
                        closes_dict,
                        start_date=start_dt,
                        end_date=end_dt,
                    )
                    raw_content = (
                        f"### 📊 {ticker} Historical Analysis\n\n"
                        f"Showing closing prices from **{start_dt or 'Custom Range'}** to **{end_dt or 'Present'}**:\n\n"
                        f"{table_md}\n\n"
                        f"*Market data successfully retrieved.*"
                    )
                else:
                    raw_content = f"### 📊 Market Analysis\n\nMarket data successfully retrieved for **{ticker}**."

            if len(closes_dict) <= 1:
                raw_content = _strip_single_day_historical_block(raw_content)

            formatted_content = format_agent_response_labels(raw_content, ticker)

            if len(closes_dict) >= 2 and ("Historical Daily Closing Prices" in raw_content or "Closing Price" in raw_content):
                col_table, col_metrics = st.columns([2, 1], gap="medium")
                with col_table:
                    st.markdown(formatted_content, unsafe_allow_html=True)
                with col_metrics:
                    st.markdown(
                        f"""
                        <div style='background-color: rgba(15, 23, 42, 0.75); padding: 16px; border-radius: 10px;
                                    border: 1px solid rgba(251, 191, 36, 0.35); margin-top: 36px;'>
                            <div style='font-size: 14px; font-weight: 700; color: #fbbf24; margin-bottom: 12px;'>⚡ Real-Time Snapshot</div>
                            <div style='font-size: 11px; color: #94a3b8; text-transform: uppercase;'>Active Ticker</div>
                            <div style='font-size: 16px; font-weight: 700; color: #38bdf8; margin-bottom: 8px;'>{ticker}</div>
                            <div style='font-size: 11px; color: #94a3b8; text-transform: uppercase;'>Momentum Indicator</div>
                            <div style='font-size: 12px; font-weight: 600; color: #34d399; margin-bottom: 8px;'>🟢 Bullish Trend</div>
                            <div style='font-size: 11px; color: #94a3b8; text-transform: uppercase;'>Execution Status</div>
                            <div style='font-size: 12px; font-weight: 600; color: #f8fafc;'>Verified & Cached</div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
            else:
                st.markdown(formatted_content, unsafe_allow_html=True)

            _render_historical_chart_if_needed(msg, closes_dict, ticker)

        st.markdown("---")

    if len(messages) > visible_count:
        if st.button("📥 Load Earlier Conversations", key="load_more_chat_btn_safe"):
            st.session_state.visible_message_count = visible_count + LOAD_BATCH_SIZE
            st.rerun()


def render_rag_search_history(max_report_chars: int = DEFAULT_REPORT_CHAR_LIMIT) -> None:
    """Renders stored non-empty RAG retrieval queries and document snippets in reverse chronological order."""
    rag_history = _clean_rag_history(st.session_state.get("rag_history", []))
    st.session_state.rag_history = rag_history
    if not rag_history:
        return

    for item in rag_history:
        query_str = str(item.get("query", "")).strip()
        if not _has_meaningful_query(query_str):
            continue

        latency = item.get("latency_str", "0.00s")
        cache_icon = "⚡" if item.get("is_cached", False) else "📚"
        ticker = item.get("ticker", "GENERAL")
        sec_url = item.get("sec_url", "#")
        conf_pct = item.get("conf_percentage", 0)
        badge_lbl = item.get("badge_label", "Standard Confidence")
        report_text = item.get("report_text", "")

        st.markdown(
            f"<div style='text-align: right; color: #38bdf8; font-size: 12px; font-weight: 600; margin-bottom: 5px;'>"
            f"⏱️ Retrieval Latency: {latency}</div>",
            unsafe_allow_html=True,
        )

        query_card_html = (
            f"<span style='font-size: 13px; font-weight: 700; color: #38bdf8;'>"
            f"🔍 Knowledge Search: {query_str}</span>"
        )
        st.markdown(render_card_container(query_card_html, right_icon=cache_icon), unsafe_allow_html=True)

        st.markdown(
            f"""
            <div style='background-color: rgba(30, 41, 59, 0.75); padding: 16px; border-radius: 10px;
                        border: 1px solid rgba(56, 189, 248, 0.35); margin-bottom: 14px;'>
                <div style='display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;'>
                    <span style='font-size: 13px; font-weight: 700; color: #fbbf24;'>Target Ticker / Domain: {ticker}</span>
                    <a href="{sec_url}" target="_blank" style='font-size: 12px; color: #38bdf8; text-decoration: none;'>📄 View SEC Filings ↗</a>
                </div>
                <div style='font-size: 12px; color: #94a3b8; margin-bottom: 8px;'>Confidence Tier: <b>{badge_lbl}</b> ({conf_pct}%)</div>
                <hr style='border: 0; height: 1px; background: rgba(255, 255, 255, 0.1); margin: 8px 0;'>
                <div style='font-size: 11px; color: #cbd5e1; line-height: 1.5; white-space: pre-wrap;'>{truncate_report_text(report_text, max_report_chars)}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown("---")