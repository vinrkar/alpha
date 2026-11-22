# src/database/repository.py

from typing import Any

from src.database.init_db import Investor, SessionLocal

def get_all_user_profiles() -> dict[str, dict[str, Any]]:
    """Fetches all investor profiles and portfolios from SQLite."""
    session = SessionLocal()
    try:
        investors = session.query(Investor).all()
        profiles: dict[str, dict[str, Any]] = {}
        for investor in investors:
            holdings: dict[str, dict[str, Any]] = {}
            for pos in investor.portfolios:
                holdings[pos.ticker] = {
                    "name": pos.name,
                    "isin": pos.isin,
                    "exchange": pos.exchange.split(", ") if "," in pos.exchange else [pos.exchange],
                    "shares": pos.shares,
                    "avg_cost": pos.avg_purchase_price,
                }
            profiles[investor.investor_id] = {
                "name": investor.name,
                "risk_tolerance": investor.risk_tolerance,
                "investment_horizon": investor.investment_horizon,
                "holdings": holdings,
            }
        return profiles
    finally:
        session.close()

def get_user_profile(user_id: str) -> dict[str, Any]:
    """Fetches a single investor profile by ID, or an empty dict if not found."""
    return get_all_user_profiles().get(user_id, {})