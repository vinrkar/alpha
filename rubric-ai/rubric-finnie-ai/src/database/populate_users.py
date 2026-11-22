# src/database/populate_users.py

import logging
import os
import secrets

from passlib.hash import bcrypt
from sqlalchemy.orm import Session

from src.database.init_db import Investor, Portfolio, SessionLocal, Staff
from src.database.profiles import CLIENT_PROFILES, STAFF_PROFILES

logger = logging.getLogger(__name__)


def _resolve_seed_password(user_id: str) -> str:
    """Resolve seed password from per-user env var, shared dev env var, or an ephemeral secret."""
    specific_pw = os.getenv(f"SEED_PW_{user_id}")
    if specific_pw:
        return specific_pw

    default_pw = os.getenv("SEED_DEFAULT_PASSWORD")
    if default_pw:
        return default_pw

    ephemeral_pw = secrets.token_urlsafe(16)
    logger.warning(
        "No SEED_PW_%s or SEED_DEFAULT_PASSWORD set; generated ephemeral password for %s: %s",
        user_id,
        user_id,
        ephemeral_pw,
    )
    return ephemeral_pw


def _seed_staff(session: Session) -> None:
    for staff_id, data in STAFF_PROFILES.items():
        raw_password = _resolve_seed_password(staff_id)
        hashed_pw = bcrypt.hash(raw_password)
        role_val = data["role"].value if hasattr(data["role"], "value") else str(data["role"])
        dept = data.get("department", "Administration")

        staff = session.get(Staff, staff_id)
        if not staff:
            session.add(
                Staff(
                    staff_id=staff_id,
                    name=data["name"],
                    password_hash=hashed_pw,
                    role=role_val,
                    department=dept,
                )
            )
        else:
            staff.name = data["name"]
            staff.password_hash = hashed_pw
            staff.role = role_val
            staff.department = dept


def _seed_investors(session: Session) -> None:
    for investor_id, data in CLIENT_PROFILES.items():
        raw_password = _resolve_seed_password(investor_id)
        hashed_pw = bcrypt.hash(raw_password)
        risk_val = (
            data["risk_tolerance"].value
            if hasattr(data["risk_tolerance"], "value")
            else str(data["risk_tolerance"])
        )
        horizon_val = (
            data["investment_horizon"].value
            if hasattr(data["investment_horizon"], "value")
            else str(data["investment_horizon"])
        )

        investor = session.get(Investor, investor_id)
        if not investor:
            session.add(
                Investor(
                    investor_id=investor_id,
                    name=data["name"],
                    password_hash=hashed_pw,
                    risk_tolerance=risk_val,
                    investment_horizon=horizon_val,
                )
            )
        else:
            investor.name = data["name"]
            investor.password_hash = hashed_pw
            investor.risk_tolerance = risk_val
            investor.investment_horizon = horizon_val

        session.query(Portfolio).filter_by(investor_id=investor_id).delete()
        for ticker, holding in data.get("holdings", {}).items():
            exchange_val = holding["exchange"]
            if isinstance(exchange_val, list):
                exchange_str = ", ".join(str(item) for item in exchange_val)
            else:
                exchange_str = str(exchange_val)

            session.add(
                Portfolio(
                    investor_id=investor_id,
                    ticker=ticker,
                    name=holding["name"],
                    isin=holding["isin"],
                    exchange=exchange_str,
                    shares=holding["shares"],
                    avg_purchase_price=holding["avg_cost"],
                )
            )


def populate_users() -> None:
    session = SessionLocal()
    try:
        logger.info("Starting staff and investor profile seeding...")
        _seed_staff(session)
        _seed_investors(session)
        session.commit()
        logger.info("Successfully seeded staff and investor profiles into SQLite.")
    except Exception as exc:
        session.rollback()
        logger.error("Error seeding database: %s", exc)
        raise
    finally:
        session.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    populate_users()