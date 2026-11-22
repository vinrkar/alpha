# src/database/profile_types.py

from enum import Enum

class StaffRole(str, Enum):
    """Standardized internal staff and administrative roles."""

    ADMIN = "System Administrator"
    COMPLIANCE = "Compliance Officer"
    SUPPORT = "Support Analyst"
    OPS_MANAGER = "Operations Manager"

class InvestmentHorizon(str, Enum):
    """Standardized mutually exclusive investment horizon categories."""

    SHORT_TERM = "Short Term (< 1 Year)"
    SHORT_MEDIUM_TERM = "Short Medium Term (1-3 Years)"
    MEDIUM_TERM = "Medium Term (3-5 Years)"
    LONG_TERM = "Long Term (5-10 Years)"
    ULTRA_LONG_TERM = "Ultra Long Term (10+ Years)"

class RiskTolerance(str, Enum):
    """Standardized investor risk tolerance categories."""

    AGGRESSIVE_GROWTH = "Aggressive Growth"
    BALANCED = "Balanced"
    CONSERVATIVE = "Conservative"
    DIVIDEND_GROWTH = "Dividend Growth"