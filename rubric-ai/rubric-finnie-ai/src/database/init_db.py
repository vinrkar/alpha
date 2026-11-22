# src/database/init_db.py

from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, create_engine, inspect
from sqlalchemy.orm import declarative_base, relationship, sessionmaker

Base = declarative_base()

BASE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
DB_FILE_PATH = DATA_DIR / "rubric-finnie-db"
DB_PATH = f"sqlite:///{DB_FILE_PATH}"

def _utc_now() -> datetime:
    return datetime.now(timezone.utc)

class Staff(Base):
    __tablename__ = "staff"

    staff_id = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False)
    password_hash = Column(String, nullable=False)
    role = Column(String, nullable=False)
    department = Column(String, default="Administration")
    created_at = Column(DateTime, default=_utc_now)
    updated_at = Column(DateTime, default=_utc_now, onupdate=_utc_now)

class Investor(Base):
    __tablename__ = "investors"

    investor_id = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False)
    password_hash = Column(String, nullable=False)
    risk_tolerance = Column(String, nullable=False)
    investment_horizon = Column(String, nullable=False)
    created_at = Column(DateTime, default=_utc_now)
    updated_at = Column(DateTime, default=_utc_now, onupdate=_utc_now)

    portfolios = relationship("Portfolio", back_populates="investor", cascade="all, delete-orphan")

class Portfolio(Base):
    __tablename__ = "portfolios"

    prtf_id = Column(Integer, primary_key=True, autoincrement=True)
    investor_id = Column(String(20), ForeignKey("investors.investor_id"), nullable=False)
    ticker = Column(String(10), nullable=False)
    name = Column(String(100), nullable=False)
    isin = Column(String(12), nullable=False)
    exchange = Column(String(50), nullable=False)
    shares = Column(Float, nullable=False)
    avg_purchase_price = Column(Float, nullable=False)
    updated_at = Column(DateTime, default=_utc_now, onupdate=_utc_now)

    investor = relationship("Investor", back_populates="portfolios")

engine = create_engine(DB_PATH, echo=False)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

def init_db() -> None:
    inspector = inspect(engine)
    existing_tables = inspector.get_table_names()

    if existing_tables:
        print(f"[SAFEGUARD] Database tables already exist at {DB_FILE_PATH}: {existing_tables}")
        print("Initialization skipped to protect existing data.")
        return

    Base.metadata.create_all(bind=engine)
    print(f"Successfully initialized clean database schema at: {DB_FILE_PATH}")

if __name__ == "__main__":
    init_db()