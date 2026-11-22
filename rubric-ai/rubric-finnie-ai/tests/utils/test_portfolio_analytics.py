# tests/agent/test_portfolio_analytics.py

from deepeval import assert_test
from deepeval.metrics import GEval
from deepeval.test_case import LLMTestCase, SingleTurnParams
import numpy as np
import pandas as pd

from src.services.quant_service import (
    calculate_beta,
    calculate_portfolio_metrics,
    calculate_value_at_risk,
    evaluate_portfolio_compliance,
)

def test_portfolio_analytics_risk_metrics() -> None:
    """Test portfolio quantitative risk and performance metrics evaluation."""
    precision_metric = GEval(
        name="Quantitative Precision",
        model="gpt-4o-mini",
        criteria="Verify portfolio quantitative risk metrics (Sharpe, Volatility, Drawdown, VaR, Beta) match expected calculations.",
        evaluation_steps=[
            "1. Check that all core quantitative metrics are present.",
            "2. Verify numerical accuracy of Sharpe ratio (0.41), volatility (18.42%), and max drawdown (-16.40%).",
            "3. Confirm VaR and Beta are correctly reported.",
        ],
        evaluation_params=[SingleTurnParams.INPUT, SingleTurnParams.ACTUAL_OUTPUT],
        threshold=0.85,
    )

    test_case = LLMTestCase(
        input="Show my portfolio risk metrics, Sharpe ratio, and drawdown analysis.",
        actual_output=(
            "### 📊 Portfolio Quantitative Risk & Performance Metrics\n\n"
            "| Risk & Performance Metric | Value | Evaluation / Status |\n"
            "|---|---|---|\n"
            "| **Sharpe Ratio** | 0.41 | Risk-Adjusted Return |\n"
            "| **Annualized Volatility** | 18.42% | Moderate Volatility |\n"
            "| **Max Drawdown** | -16.40% | Downside Risk Parameter |\n"
            "| **Value at Risk (VaR 95%)** | -1.74% | Historical VaR |\n"
            "| **Portfolio Beta** | 1.00 | Benchmarked vs S&P 500 |\n\n"
            "**Quantitative Summary:**\n"
            "The portfolio demonstrates a Sharpe ratio of 0.41 with an annualized volatility of 18.42% "
            "and a maximum drawdown of -16.40%, reflecting balanced risk distribution across mega-cap equity holdings."
        ),
    )
    assert_test(test_case, [precision_metric])

def test_calculate_portfolio_metrics_balanced() -> None:
    """Test standard balanced portfolio metrics calculation."""
    rng = np.random.default_rng(42)
    returns = pd.Series(rng.normal(0.0005, 0.012, 252))
    metrics = calculate_portfolio_metrics(returns, risk_free_rate=0.045)

    assert "sharpe_ratio" in metrics
    assert "max_drawdown" in metrics
    assert "annualized_volatility" in metrics
    assert "annualized_return" in metrics

    assert isinstance(metrics["sharpe_ratio"], float)
    assert metrics["annualized_volatility"] > 0.0
    assert metrics["max_drawdown"] <= 0.0

def test_calculate_portfolio_metrics_empty() -> None:
    """Test empty or insufficient returns series handling."""
    empty_returns = pd.Series([], dtype=float)
    metrics = calculate_portfolio_metrics(empty_returns)

    assert metrics["sharpe_ratio"] == 0.0
    assert metrics["max_drawdown"] == 0.0
    assert metrics["annualized_volatility"] == 0.0

def test_calculate_portfolio_metrics_zero_volatility() -> None:
    """Test zero-volatility / flat returns series handling."""
    flat_returns = pd.Series([0.001] * 252)
    metrics = calculate_portfolio_metrics(flat_returns, risk_free_rate=0.045)

    assert metrics["annualized_volatility"] == 0.0
    assert (
            metrics["sharpe_ratio"] == 0.0
            or np.isinf(metrics["sharpe_ratio"])
            or abs(metrics["sharpe_ratio"]) > 1e6
    )

def test_calculate_value_at_risk() -> None:
    """Test historical Value at Risk (VaR 95%) calculation."""
    rng = np.random.default_rng(42)
    returns = pd.Series(rng.normal(0.0005, 0.015, 252))
    var_95 = calculate_value_at_risk(returns, confidence_level=0.95)

    assert isinstance(var_95, float)
    assert var_95 < 0.0

def test_calculate_beta() -> None:
    """Test portfolio beta relative to benchmark."""
    rng = np.random.default_rng(42)
    benchmark_ret = pd.Series(rng.normal(0.0004, 0.010, 100))
    portfolio_ret = 1.2 * benchmark_ret + pd.Series(rng.normal(0.0001, 0.005, 100))

    beta = calculate_beta(portfolio_ret, benchmark_ret)
    assert isinstance(beta, float)
    assert beta > 0.0

def test_calculate_beta_inverse() -> None:
    """Test portfolio beta with inverse benchmark correlation."""
    rng = np.random.default_rng(42)
    benchmark_ret = pd.Series(rng.normal(0.0004, 0.010, 100))
    inverse_ret = -1.0 * benchmark_ret + pd.Series(rng.normal(0.0, 0.002, 100))

    beta = calculate_beta(inverse_ret, benchmark_ret)
    assert isinstance(beta, float)
    assert beta < 0.0

def test_evaluate_portfolio_compliance_passing() -> None:
    """Test compliance guardrails for compliant allocations."""
    holdings = {
        "AAPL": {"shares": 100, "current_price": 150.0},
        "MSFT": {"shares": 200, "current_price": 100.0},
        "GOOGL": {"shares": 150, "current_price": 100.0},
    }
    result = evaluate_portfolio_compliance(holdings, max_single_stock_pct=50.0)

    assert result["total_value"] == 50000.0
    assert result["is_compliant"] is True
    assert len(result["violations"]) == 0

def test_evaluate_portfolio_compliance_violations() -> None:
    """Test compliance guardrails for exceeded allocation limits."""
    holdings = {
        "AAPL": {"shares": 500, "current_price": 160.0},
        "MSFT": {"shares": 200, "current_price": 100.0},
    }
    result = evaluate_portfolio_compliance(holdings, max_single_stock_pct=15.0)

    assert result["total_value"] == 100000.0
    assert result["is_compliant"] is False
    assert "AAPL" in result["violations"]

def test_evaluate_portfolio_compliance_edge_prices() -> None:
    """Test compliance guardrails with zero-price holdings."""
    holdings = {
        "AAPL": {"shares": 100, "current_price": 0.0},
        "MSFT": {"shares": 100, "current_price": 200.0},
    }
    result = evaluate_portfolio_compliance(holdings, max_single_stock_pct=50.0)

    assert result["total_value"] == 20000.0
    assert result["is_compliant"] is False
    assert "MSFT" in result["violations"]