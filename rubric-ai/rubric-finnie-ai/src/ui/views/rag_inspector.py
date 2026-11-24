import logging
import os
import re
import time
import uuid
from typing import Any

import streamlit as st

from src.core.guardrails import sanitize_and_validate_input
from src.core.llm_client import get_embedding
from src.core.redis_client import get_semantic_cache, set_semantic_cache
from src.rag.vector_store import FinancialVectorStore
from src.ui.components.helpers import (
    add_rag_search_to_history,
    render_clear_rag_history_button,
    render_rag_search_history,
    run_async,
)
from src.ui.components.styles import render_subheader_card
from src.utils.rag_utils import get_confidence_percentage, get_confidence_tier

logger = logging.getLogger(__name__)

EXCLUDED_CAPS = {"A", "I", "AN", "THE", "AND", "FOR", "TO", "IN", "ON", "Q", "K"}
MACRO_KEYWORDS = ("fed", "federal", "reserve", "rate", "fomc", "benchmark", "inflation")
RISK_KEYWORDS = ("limit", "position", "risk", "portfolio", "standard", "allocation", "single-stock")
STOPWORDS = {
    "how", "what", "did", "the", "in", "latest", "filing", "quarter",
    "annual", "report", "revenue", "earnings", "trend", "and", "is",
    "of", "for", "year", "over", "10-q", "10-k", "statement", "some",
    "growth", "co's",
}


def _is_valid_query(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    normalized = re.sub(r"[\s\u00a0\u200b\u200c\u200d\ufeff]+", "", value).strip("\"'`")
    return bool(normalized)


def _normalize_query(raw_query: Any) -> str:
    if not isinstance(raw_query, str):
        return ""
    cleaned = re.sub(r"[\s\u00a0\u200b\u200c\u200d\ufeff]+", " ", raw_query).strip()
    return cleaned if _is_valid_query(cleaned) else ""


def _infer_target_ticker_or_domain(query: str, holdings: dict[str, Any]) -> str:
    parenthetical = re.search(r"\(([A-Za-z]{1,5})\)", query)
    if parenthetical:
        return parenthetical.group(1).upper()

    for match in re.finditer(r"\b([A-Z]{2,5})\b", query):
        candidate = match.group(1).upper()
        if candidate not in EXCLUDED_CAPS:
            return candidate

    query_lower = query.lower()
    for ticker, info in holdings.items():
        comp_name = str(info.get("name", "")).lower()
        if ticker.lower() in query_lower or (comp_name and comp_name in query_lower):
            return ticker.upper()

    if any(kw in query_lower for kw in RISK_KEYWORDS):
        return "PORTFOLIO"
    if any(kw in query_lower for kw in MACRO_KEYWORDS):
        return "MACRO"

    words = [
        word.strip(".,?!'\"")
        for word in query.split()
        if word and word[0].isupper() and len(word) >= 2 and word.lower() not in STOPWORDS
    ]
    return words[0][:5].upper() if words else "GENERAL"


def _query_chromadb(query: str, fallback_ticker: str) -> tuple[str, str, float]:
    collection_name = os.getenv("CHROMA_COLLECTION_NAME", "finnieai_db")
    store = FinancialVectorStore(collection_name=collection_name)

    if not store.collection:
        raise RuntimeError(
            f"ChromaDB collection '{collection_name}' is unavailable. "
            "Check CHROMA_HOST, CHROMA_PORT, and auth settings."
        )

    results = store.collection.query(
        query_texts=[query],
        n_results=1,
        include=["documents", "metadatas", "distances"],
    )

    if results and results.get("documents") and results["documents"][0]:
        report_text = results["documents"][0][0]
        metadata_list = results.get("metadatas") or [[]]
        metadata = metadata_list[0][0] if metadata_list and metadata_list[0] else {}
        resolved_ticker = metadata.get("ticker", fallback_ticker)

        rrf_score = 0.0350
        distances_list = results.get("distances") or [[]]
        if distances_list and distances_list[0]:
            dist = distances_list[0][0]
            rrf_score = round(max(0.001, 1.0 / (1.0 + dist)), 4)
        return report_text, resolved_ticker, rrf_score

    return (
        f"⚠️ No matching documents found in collection '{collection_name}' for query: '{query}'.",
        fallback_ticker,
        0.0100,
    )


def render_rag_inspector_tab(active_user_data: dict[str, Any]) -> None:
    render_subheader_card(
        "📚 Hybrid RAG Knowledge Base Inspector",
        subtitle="Inspect indexed SEC filings, Federal Reserve notes, and valuation frameworks.",
    )

    status_container = st.empty()
    rag_query = st.chat_input(
        "🔍  SEC 10-Q/10-K filings, revenue growth, Federal Reserve notes, or valuation frameworks...",
        key="rag_chat_input",
    )

    render_clear_rag_history_button(key="clear_rag_history_below_input_btn")

    if rag_query is not None:
        normalized_input = _normalize_query(rag_query)

        if not normalized_input:
            st.warning("⚠️ Please type a financial research question or ticker before searching.")
        else:
            search_start_time = time.time()
            is_safe, clean_input, err_msg = sanitize_and_validate_input(normalized_input)
            final_query = _normalize_query(clean_input)

            if not is_safe:
                st.error(
                    f"🛡️ Request Blocked for {normalized_input!r}: "
                    f"{err_msg or 'Query includes instructions outside safe financial research.'}"
                )
            elif not final_query:
                st.warning("⚠️ Please type a financial research question or ticker before searching.")
            else:
                logger.info("Executing RAG search query='%s'", final_query)
                elapsed = time.time() - search_start_time
                status_container.markdown(
                    f"<div style='color: #38bdf8; font-weight: 600; font-size: 13px; margin-bottom: 8px;'>"
                    f"⏱️ Executing Knowledge Base Hybrid Retrieval... ({elapsed:.2f}s)</div>",
                    unsafe_allow_html=True,
                )

                is_private = any(
                    kw in final_query.lower()
                    for kw in ("portfolio", "holding", "my asset", "allocation", "balance")
                )
                resolved_user_id = active_user_data.get("user_id", "default_user")
                scope_key = f"user:{resolved_user_id}" if is_private else "global"

                query_embedding = get_embedding(final_query)
                cached_payload = (
                    run_async(
                        get_semantic_cache(
                            query_embedding,
                            scope_key=scope_key,
                            query_text=final_query,
                            threshold=0.85,
                        )
                    )
                    if query_embedding
                    else None
                )

                if cached_payload:
                    is_cached = True
                    target_t = cached_payload["ticker"]
                    sec_search_url = cached_payload["sec_url"]
                    conf_percentage = cached_payload["conf_percentage"]
                    badge_label = cached_payload["badge_label"]
                    badge_desc = cached_payload["badge_desc"]
                    raw_rrf_score = cached_payload["raw_rrf_score"]
                    report_text = cached_payload["report_text"]
                    latency_str = f"{time.time() - search_start_time:.3f}s"
                else:
                    is_cached = False
                    inferred_ticker = _infer_target_ticker_or_domain(
                        final_query,
                        active_user_data.get("holdings", {}),
                    )
                    try:
                        report_text, target_t, raw_rrf_score = _query_chromadb(
                            final_query, inferred_ticker
                        )
                    except Exception as exc:
                        logger.error("ChromaDB query failed: %s", exc)
                        report_text = f"⚠️ Error querying ChromaDB container: {exc}"
                        target_t = inferred_ticker
                        raw_rrf_score = 0.0100

                    sec_search_url = f"https://www.sec.gov/edgar/search/#/q={target_t}"
                    conf_percentage = get_confidence_percentage(raw_rrf_score)
                    badge_label, badge_desc = get_confidence_tier(conf_percentage)
                    latency_str = f"{time.time() - search_start_time:.2f}s"

                    if query_embedding and not report_text.startswith("⚠️"):
                        run_async(
                            set_semantic_cache(
                                query_embedding=query_embedding,
                                scope_key=scope_key,
                                query_text=final_query,
                                response_data={
                                    "ticker": target_t,
                                    "sec_url": sec_search_url,
                                    "conf_percentage": conf_percentage,
                                    "badge_label": badge_label,
                                    "badge_desc": badge_desc,
                                    "raw_rrf_score": raw_rrf_score,
                                    "report_text": report_text,
                                },
                            )
                        )

                status_container.empty()
                if _is_valid_query(final_query):
                    add_rag_search_to_history(
                        {
                            "query": final_query,
                            "ticker": target_t,
                            "sec_url": sec_search_url,
                            "conf_percentage": conf_percentage,
                            "badge_label": badge_label,
                            "badge_desc": badge_desc,
                            "raw_rrf_score": raw_rrf_score,
                            "latency_str": latency_str,
                            "report_text": report_text,
                            "is_cached": is_cached,
                            "render_id": uuid.uuid4().hex[:8],
                        }
                    )
                st.rerun()

    st.markdown("---")
    render_rag_search_history(max_report_chars=2500)
