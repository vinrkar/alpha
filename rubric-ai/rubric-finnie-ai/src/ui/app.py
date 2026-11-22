import logging
import sys
from pathlib import Path

root_dir = Path(__file__).resolve().parent.parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

import streamlit as st
from cryptography.fernet import Fernet
from passlib.hash import bcrypt

from src.core.config import settings
from src.database.init_db import Investor, SessionLocal, Staff
from src.services.market_data_service import fetch_user_profiles
from src.ui.components.helpers import init_persistent_session, render_top_header
from src.ui.components.styles import apply_custom_theme
from src.ui.views.assistant_chat import render_assistant_chat_tab
from src.ui.views.market_intel import render_market_intelligence_tab
from src.ui.views.order_execution import render_order_execution_tab
from src.ui.views.portfolio_analytics import render_portfolio_analytics_tab
from src.ui.views.rag_inspector import render_rag_inspector_tab

logger = logging.getLogger(__name__)

CHAT_API_URL = settings.CHAT_API_URL
cipher = Fernet(settings.SESSION_ENCRYPTION_KEY.encode())

st.set_page_config(
    page_title="Rubric Finnie AI - Financial Assistant",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)


@st.cache_data(ttl=300, show_spinner=False)
def _cached_fetch_profiles() -> dict:
    return fetch_user_profiles()


def _enforce_clean_token_query_param() -> None:
    query_params = st.query_params
    if "token" in query_params:
        extra_keys = [k for k in query_params.keys() if k != "token"]
        if extra_keys:
            token_val = query_params["token"]
            st.query_params.clear()
            st.query_params["token"] = token_val
            st.rerun()


def _restore_session_from_token() -> None:
    query_params = st.query_params
    if st.session_state.get("authenticated") or "token" not in query_params:
        return
    try:
        decrypted_data = cipher.decrypt(query_params["token"].encode()).decode()
        user_id, role = decrypted_data.split(":", maxsplit=1)
        st.session_state.authenticated = True
        st.session_state.active_user_id = user_id
        st.session_state.user_role = role
        st.session_state.session_id = f"session_{user_id}"
        init_persistent_session()
    except Exception as exc:
        logger.error("Failed to decrypt session token: %s", exc)
        st.query_params.clear()


def _authenticate_credentials(username: str, password: str) -> tuple[bool, str]:
    session = SessionLocal()
    try:
        if username.startswith("R"):
            staff_member = session.get(Staff, username)
            if staff_member and bcrypt.verify(password, staff_member.password_hash):
                return True, "Admin"
        else:
            investor = session.get(Investor, username)
            if investor and bcrypt.verify(password, investor.password_hash):
                return True, "Client"
        return False, "Client"
    finally:
        session.close()


def _render_login_gate() -> None:
    st.title("🔐 Rubric Finnie AI – Enterprise Login")
    st.markdown("Please enter your assigned 8-character Profile ID and password.")

    col_form, _ = st.columns([1, 2])
    with col_form:
        input_user = st.text_input("Username / Profile ID")
        input_pass = st.text_input("Password", type="password")

        if st.button("Sign In"):
            valid, role = _authenticate_credentials(input_user.strip(), input_pass)
            if valid:
                st.session_state.authenticated = True
                st.session_state.user_role = role
                st.session_state.active_user_id = input_user.strip()
                st.session_state.session_id = f"session_{input_user.strip()}"
                init_persistent_session()

                secure_token = cipher.encrypt(f"{input_user.strip()}:{role}".encode()).decode()
                st.query_params.clear()
                st.query_params["token"] = secure_token
                st.rerun()
            else:
                st.error("Invalid ID or incorrect password.")
    st.stop()


profiles_store = _cached_fetch_profiles()
init_persistent_session()
_enforce_clean_token_query_param()
_restore_session_from_token()

if not st.session_state.get("authenticated"):
    _render_login_gate()

active_user_id = st.session_state.active_user_id

st.sidebar.title("⚙️ Rubric Finnie AI Control Center")
st.sidebar.markdown(f"**Logged in as:** `{active_user_id}`")
st.sidebar.markdown("---")

selected_admin_target = None
if st.session_state.user_role == "Admin":
    st.sidebar.markdown("### 🛡️ Admin Controls")
    admin_profile_options = {
        uid: f"{data.get('name', uid)} ({data.get('risk_tolerance', 'Admin/Standard')})"
        for uid, data in profiles_store.items()
    }
    selected_admin_target = st.sidebar.selectbox(
        "Inspect Investor Profile",
        options=list(admin_profile_options.keys()),
        format_func=lambda x: admin_profile_options[x],
    )
    active_user_data = profiles_store.get(selected_admin_target, {})
else:
    active_user_data = profiles_store.get(active_user_id, {})

current_risk = active_user_data.get("risk_tolerance", "Balanced")
theme_data = apply_custom_theme(current_risk)

st.sidebar.markdown(
    f"""
    <div class="sidebar-strategy-card">
        <span style="font-size: 11px; text-transform: uppercase; letter-spacing: 1px; color: #94a3b8;">Investor Profile</span>
        <div style="font-size: 16px; font-weight: bold; color: #f8fafc; margin-top: 4px;">{active_user_data.get('name', 'N/A')}</div>
        <div style="font-size: 13px; color: #38bdf8; margin-top: 4px;">{theme_data['badge']}</div>
        <hr style="margin: 8px 0; border-color: rgba(255, 255, 255, 0.1);">
        <div style="font-size: 12px; color: #cbd5e1;"><b>Horizon:</b> {active_user_data.get('investment_horizon', 'N/A')}</div>
        <div style="font-size: 12px; color: #cbd5e1; margin-top: 2px;"><b>Tracked Assets:</b> {len(active_user_data.get('holdings', {}))} tickers</div>
    </div>
    """,
    unsafe_allow_html=True,
)

st.sidebar.markdown("---")
st.sidebar.markdown("### 🛡️ Account Safety & Status")
st.sidebar.markdown("- **Security Standard:** SOC-2 Type II Certified")
st.sidebar.markdown("- **Data Feed Status:** Real-Time (NYSE / NASDAQ)")
st.sidebar.markdown("- **Engine Mode:** Automated Risk Guardrails Active")

render_top_header()
st.markdown("<div style='margin-top: 24px;'></div>", unsafe_allow_html=True)

tab_order, tab_market, tab_portfolio, tab_rag, tab_chat = st.tabs(
    [
        "📈 Order Execution",
        "📊 Market Intelligence",
        "💼 Portfolio Analytics",
        "📚 Knowledge Base & RAG",
        "💬 Assistant Chat",
    ]
)

with tab_order:
    render_order_execution_tab(active_user_id, active_user_data, selected_admin_target, CHAT_API_URL)

with tab_market:
    render_market_intelligence_tab(active_user_data)

with tab_portfolio:
    render_portfolio_analytics_tab(active_user_id, active_user_data)

with tab_rag:
    render_rag_inspector_tab(active_user_data)

with tab_chat:
    render_assistant_chat_tab(active_user_id, active_user_data, selected_admin_target, CHAT_API_URL)