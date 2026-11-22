import logging
import streamlit as st

logger = logging.getLogger(__name__)

STRATEGY_CONFIG: dict[str, dict[str, str]] = {
    "Aggressive Growth": {
        "sidebar_bg": "https://images.unsplash.com/photo-1620712943543-bcc4688e7485?q=80&w=1000&auto=format&fit=crop",
        "badge": "🚀 Aggressive Growth",
    },
    "Balanced": {
        "sidebar_bg": "https://images.unsplash.com/photo-1486406146926-c627a92ad1ab?q=80&w=1000&auto=format&fit=crop",
        "badge": "⚖️ Balanced",
    },
    "Conservative": {
        "sidebar_bg": "https://images.unsplash.com/photo-1507679799987-c73779587ccf?q=80&w=1000&auto=format&fit=crop",
        "badge": "🛡️ Conservative",
    },
    "Dividend Growth": {
        "sidebar_bg": "https://images.unsplash.com/photo-1590283603385-17ffb3a7f29f?q=80&w=1000&auto=format&fit=crop",
        "badge": "💰 Dividend Growth",
    },
}

def format_volume_num(val) -> str:
    try:
        v = float(val)
        if v >= 1e12:
            return f"{v / 1e12:,.2f}T"
        if v >= 1e9:
            return f"{v / 1e9:,.2f}B"
        if v >= 1e6:
            return f"{v / 1e6:,.2f}M"
        if v >= 1e3:
            return f"{v / 1e3:,.2f}K"
        return f"{v:,.2f}"
    except (TypeError, ValueError) as exc:
        logger.debug("Failed to format volume %r: %s", val, exc)
        return str(val)

def format_market_cap_num(val) -> str:
    try:
        v = float(val)
        if v >= 1e12:
            return f"${v / 1e12:,.2f}T"
        if v >= 1e9:
            return f"${v / 1e9:,.2f}B"
        if v >= 1e6:
            return f"${v / 1e6:,.2f}M"
        return f"${v:,.2f}"
    except (TypeError, ValueError) as exc:
        logger.debug("Failed to format market cap %r: %s", val, exc)
        return "N/A"

def apply_custom_theme(current_risk: str) -> dict[str, str]:
    theme_data = STRATEGY_CONFIG.get(current_risk, STRATEGY_CONFIG["Balanced"])
    bg_url = theme_data["sidebar_bg"]

    st.markdown(
        f"""
        <style>
        .stApp {{
            background: linear-gradient(135deg, #0b132b 0%, #1c2541 50%, #3a506b 100%);
            background-attachment: fixed;
        }}
        [data-testid="stSidebar"] {{
            background-color: #080c14;
            border-right: 1px solid rgba(255, 255, 255, 0.08);
        }}
        .sidebar-strategy-card {{
            background: linear-gradient(rgba(15, 23, 42, 0.45), rgba(15, 23, 42, 0.55)), url("{bg_url}");
            background-size: cover;
            background-position: center;
            padding: 16px;
            border-radius: 10px;
            border: 1px solid rgba(255, 255, 255, 0.25);
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
            margin-bottom: 16px;
        }}
        .main h3 {{
            font-size: 1.15rem !important;
            font-weight: 600 !important;
            color: #f8fafc !important;
            letter-spacing: -0.2px !important;
            margin-top: 10px !important;
            margin-bottom: 15px !important;
        }}
        :not([data-testid="stDialog"]) div[data-testid="stColumn"]:not(.action-col) div[data-testid="stButton"] button[kind="secondary"] {{
            background-color: transparent !important;
            border: none !important;
            border-radius: 0 !important;
            box-shadow: none !important;
            padding: 0 !important;
            min-height: unset !important;
            height: 24px !important;
            line-height: 24px !important;
            text-align: left !important;
            display: flex !important;
            align-items: center !important;
            width: 100% !important;
        }}
        :not([data-testid="stDialog"]) div[data-testid="stColumn"]:not(.action-col) div[data-testid="stButton"] button[kind="secondary"] p {{
            font-size: 11px !important;
            font-weight: 700 !important;
            color: #38bdf8 !important;
            margin: 0 !important;
            padding: 0 !important;
        }}
        :not([data-testid="stDialog"]) div[data-testid="stColumn"]:not(.action-col) div[data-testid="stButton"] button[kind="secondary"]:hover {{
            background-color: rgba(56, 189, 248, 0.1) !important;
            border: none !important;
            box-shadow: none !important;
        }}
        div[data-testid="stForm"] label p,
        div[data-testid="stVerticalBlock"] label p,
        div[data-testid="column"] label p,
        .terminal-field-label {{
            font-size: 11px !important;
            font-weight: 700 !important;
            color: #38bdf8 !important;
            text-transform: uppercase !important;
            letter-spacing: 0.5px !important;
        }}
        .table-cell-truncate {{
            white-space: nowrap !important;
            overflow: hidden !important;
            text-overflow: ellipsis !important;
            font-size: 11px !important;
            line-height: 22px !important;
        }}
        .table-cell-nowrap {{
            white-space: nowrap !important;
            font-size: 11px !important;
            line-height: 22px !important;
        }}
        [data-testid="stMetricValue"] {{
            font-size: 1.35rem !important;
            font-weight: 600 !important;
            color: #38bdf8 !important;
        }}
        [data-testid="stMetricLabel"] {{
            font-size: 0.8rem !important;
            color: #94a3b8 !important;
            text-transform: uppercase !important;
            letter-spacing: 0.5px !important;
        }}
        .subheader-card {{
            background-color: rgba(15, 23, 42, 0.6);
            padding: 14px 18px;
            border-radius: 12px;
            border: 1px solid rgba(56, 189, 248, 0.2);
            box-shadow: 0 4px 16px rgba(0, 0, 0, 0.3);
            margin-bottom: 18px;
            margin-top: 10px;
        }}
        .subheader-card-title {{
            font-size: 14px;
            font-weight: 700;
            color: #38bdf8;
            letter-spacing: 0.3px;
        }}
        .data-header-card {{
            background-color: rgba(30, 27, 20, 0.65);
            padding: 12px 16px;
            border-radius: 10px;
            border: 1px solid rgba(245, 158, 11, 0.35);
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
            margin-bottom: 14px;
            margin-top: 12px;
        }}
        .data-header-card-title {{
            font-size: 13px;
            font-weight: 700;
            color: #fbbf24;
            letter-spacing: 0.3px;
        }}
        .kpi-card {{
            background-color: rgba(30, 41, 59, 0.75);
            padding: 14px 16px;
            border-radius: 10px;
            border: 1px solid rgba(56, 189, 248, 0.25);
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
        }}
        .kpi-card-label {{
            font-size: 11px;
            font-weight: 700;
            color: #94a3b8;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 6px;
        }}
        .kpi-card-value {{
            font-size: 22px;
            font-weight: 700;
            color: #f8fafc;
        }}
        .kpi-mini-card {{
            background-color: rgba(30, 41, 59, 0.75);
            padding: 12px 10px;
            border-radius: 8px;
            border: 1px solid rgba(56, 189, 248, 0.2);
            box-shadow: 0 4px 10px rgba(0, 0, 0, 0.25);
            text-align: center;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )
    return theme_data

def render_subheader_card(title: str, subtitle: str | None = None) -> None:
    sub_html = (
        f'<div style="font-size: 12px; color: #94a3b8; margin-top: 4px;">{subtitle}</div>'
        if subtitle
        else ""
    )
    st.markdown(
        f"""
        <div class="subheader-card">
            <span class="subheader-card-title">{title}</span>
            {sub_html}
        </div>
        """,
        unsafe_allow_html=True,
    )

def render_data_header_card(title: str) -> None:
    st.markdown(
        f"""
        <div class="data-header-card">
            <span class="data-header-card-title">{title}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

def render_kpi_card(label: str, value_html: str, sub_html: str = "") -> None:
    st.markdown(
        f"""
        <div class="kpi-card">
            <div class="kpi-card-label">{label}</div>
            <div class="kpi-card-value">{value_html}</div>
            {sub_html}
        </div>
        """,
        unsafe_allow_html=True,
    )

def render_mini_kpi_card(label: str, value: str, subtitle: str, value_color: str) -> None:
    st.markdown(
        f"""
        <div class="kpi-mini-card">
            <div style="font-size: 10px; font-weight: 700; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.3px; margin-bottom: 4px;">{label}</div>
            <div style="font-size: 17px; font-weight: 700; color: {value_color};">{value}</div>
            <div style="font-size: 10px; color: #38bdf8; margin-top: 3px; font-weight: 500;">{subtitle}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )