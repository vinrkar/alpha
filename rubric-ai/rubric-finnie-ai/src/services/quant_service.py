import logging
from typing import Any

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

def calculate_portfolio_metrics(
        returns_series: pd.Series,
        risk_free_rate: float = 0.045,
) -> dict[str, float]:
    """Computes annualized Sharpe ratio, Max Drawdown, Volatility, and Return."""
    if returns_series.empty or len(returns_series) < 2:
        logger.debug("Returns series empty or insufficient for quantitative metrics.")
        return {
            "sharpe_ratio": 0.0,
            "max_drawdown": 0.0,
            "annualized_volatility": 0.0,
            "annualized_return": 0.0,
        }

    trading_days = 252
    mean_ret = returns_series.mean()
    daily_vol = returns_series.std()

    ann_ret = ((1 + mean_ret) ** trading_days) - 1
    ann_vol = daily_vol * np.sqrt(trading_days)
    excess = ann_ret - risk_free_rate
    sharpe = (excess / ann_vol) if ann_vol > 0 else 0.0

    cum_ret = (1 + returns_series).cumprod()
    peak = cum_ret.cummax()
    max_dd = ((cum_ret - peak) / peak).min()

    return {
        "sharpe_ratio": round(float(sharpe), 4),
        "max_drawdown": round(float(max_dd), 4),
        "annualized_volatility": round(float(ann_vol), 4),
        "annualized_return": round(float(ann_ret), 4),
    }

def calculate_value_at_risk(
        returns_series: pd.Series,
        confidence_level: float = 0.95,
) -> float:
    """Calculates historical Value at Risk (VaR) at the specified confidence level."""
    if returns_series.empty:
        return 0.0
    return round(float(np.percentile(returns_series, (1.0 - confidence_level) * 100)), 4)

def calculate_beta(
        portfolio_returns: pd.Series,
        benchmark_returns: pd.Series,
) -> float:
    """Calculates portfolio Beta relative to a benchmark series."""
    if portfolio_returns.empty or benchmark_returns.empty:
        return 1.0

    aligned = pd.concat([portfolio_returns, benchmark_returns], axis=1).dropna()
    if len(aligned) < 2:
        return 1.0

    cov = np.cov(aligned.iloc[:, 0], aligned.iloc[:, 1])[0][1]
    var = np.var(aligned.iloc[:, 1])
    return round(float(cov / var), 4) if var > 0 else 1.0

def evaluate_portfolio_compliance(
        holdings_dict: dict[str, dict[str, Any]],
        max_single_stock_pct: float = 15.0,
) -> dict[str, Any]:
    """Evaluates single-position concentration limits across portfolio holdings."""
    logger.info("Evaluating portfolio compliance across %d holdings.", len(holdings_dict))
    total_value = 0.0
    position_values: dict[str, float] = {}

    for ticker, info in holdings_dict.items():
        shares = float(info.get("shares", 0))
        price = float(info.get("current_price", info.get("avg_cost", 0)))
        val = shares * price
        position_values[ticker] = val
        total_value += val

    violations: list[str] = []
    summary_rows: list[dict[str, Any]] = []
    for ticker, val in position_values.items():
        weight = (val / total_value * 100) if total_value > 0 else 0.0
        status = "COMPLIES" if weight <= max_single_stock_pct else "EXCEEDS LIMIT"
        if weight > max_single_stock_pct:
            violations.append(ticker)
        summary_rows.append(
            {
                "ticker": ticker,
                "value": val,
                "weight": weight,
                "status": status,
            }
        )

    return {
        "total_value": total_value,
        "summary_rows": summary_rows,
        "is_compliant": len(violations) == 0,
        "violations": violations,
    }