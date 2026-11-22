import logging
from typing import Any

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from src.core.guardrails import validate_trade_price_boundaries
from src.database.init_db import DB_PATH, Portfolio
from src.tools.yfinance_tool import fetch_live_market_data

logger = logging.getLogger(__name__)

engine = create_engine(DB_PATH, echo=False)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

def _apply_buy(
        session: Session,
        existing_holding: Portfolio | None,
        user_id: str,
        ticker: str,
        shares: float,
        price: float,
        live_info: dict[str, Any],
) -> None:
    if existing_holding:
        old_shares = float(existing_holding.shares)
        old_avg_cost = float(existing_holding.avg_purchase_price)
        new_shares = old_shares + shares
        new_avg_cost = ((old_shares * old_avg_cost) + (shares * price)) / new_shares
        existing_holding.shares = new_shares
        existing_holding.avg_purchase_price = new_avg_cost
        return

    asset_name = live_info.get("name", ticker)
    isin = live_info.get("isin", f"US{abs(hash(ticker)) % 10000000000:010d}")
    exchange = live_info.get("exchange", "NASDAQ")
    if isinstance(exchange, list):
        exchange = ", ".join(str(item) for item in exchange)

    session.add(
        Portfolio(
            investor_id=user_id,
            ticker=ticker,
            name=asset_name,
            isin=isin,
            exchange=exchange,
            shares=float(shares),
            avg_purchase_price=float(price),
        )
    )

def _apply_sell(
        session: Session,
        existing_holding: Portfolio | None,
        user_id: str,
        ticker: str,
        shares: float,
        price: float,
) -> None:
    if not existing_holding:
        raise ValueError(f"Ticker '{ticker}' not found in portfolio holdings for user {user_id}.")

    old_shares = float(existing_holding.shares)
    old_avg_cost = float(existing_holding.avg_purchase_price)

    if shares > old_shares:
        raise ValueError(
            f"Cannot sell {shares} shares. User only holds {old_shares} shares of {ticker}."
        )

    new_shares = old_shares - shares
    if new_shares == 0:
        session.delete(existing_holding)
        return

    remaining_cost = max(0.0, (old_shares * old_avg_cost) - (shares * price))
    existing_holding.shares = new_shares
    existing_holding.avg_purchase_price = remaining_cost / new_shares

def execute_trade(
        user_id: str,
        ticker: str,
        action: str,
        shares: float,
        price: float,
) -> dict[str, str]:
    clean_ticker = ticker.upper().strip()
    action_upper = action.upper().strip()

    if shares <= 0:
        raise ValueError("Share quantity must be greater than zero.")
    if price <= 0:
        raise ValueError("Execution price must be greater than zero.")
    if action_upper not in {"BUY", "SELL"}:
        raise ValueError("Invalid trade action. Must be 'BUY' or 'SELL'.")

    live_info = fetch_live_market_data(clean_ticker)
    if not isinstance(live_info, dict) or not live_info.get("current_price"):
        raise ValueError(
            f"Invalid or unsupported ticker symbol '{clean_ticker}'. Please enter a valid stock ticker."
        )

    validate_trade_price_boundaries(clean_ticker, price, live_info)

    session = SessionLocal()
    try:
        existing_holding = (
            session.query(Portfolio)
            .filter_by(investor_id=user_id, ticker=clean_ticker)
            .first()
        )

        if action_upper == "BUY":
            _apply_buy(session, existing_holding, user_id, clean_ticker, shares, price, live_info)
        else:
            _apply_sell(session, existing_holding, user_id, clean_ticker, shares, price)

        session.commit()
        total_tx_val = shares * price
        tx_label = "Est. Debit (-)" if action_upper == "BUY" else "Est. Credit (+)"

        return {
            "status": "success",
            "message": (
                f"Successfully executed {action_upper} order for {shares:,.4f} shares of "
                f"{clean_ticker} at ${price:,.2f} | {tx_label}: ${total_tx_val:,.2f}"
            ),
        }
    except Exception as exc:
        session.rollback()
        logger.error("Trade execution failed for user=%s ticker=%s: %s", user_id, clean_ticker, exc)
        raise
    finally:
        session.close()