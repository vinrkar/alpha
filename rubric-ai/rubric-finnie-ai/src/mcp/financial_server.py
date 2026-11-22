# src/mcp/servers/financial_server.py

import logging
import sys

from mcp.server.mcpserver import MCPServer
import pandas as pd
import yfinance as yf

logging.basicConfig(level=logging.INFO, stream=sys.stderr)
logger = logging.getLogger("financial-market-server")

app = MCPServer("financial-market-server")

@app.tool()
def fetch_historical_prices(ticker: str, start_date: str, end_date: str) -> str:
    """Fetch daily historical stock prices for a given ticker, start date, and end date."""
    logger.info(
        "MCP tool 'fetch_historical_prices' invoked | ticker=%s, start=%s, end=%s",
        ticker,
        start_date,
        end_date,
    )
    try:
        df = yf.download(ticker, start=start_date, end=end_date, timeout=15)
        if df.empty:
            return f"No data found for {ticker} between {start_date} and {end_date}."

        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        df.index = pd.to_datetime(df.index)
        df = df.loc[start_date:end_date]
        if df.empty:
            return f"No data found for {ticker} between {start_date} and {end_date}."

        df_reset = df.reset_index()
        date_col = "Date" if "Date" in df_reset.columns else df_reset.columns[0]
        df_reset[date_col] = pd.to_datetime(df_reset[date_col]).dt.strftime("%Y-%m-%d")

        return df_reset.to_json(orient="records", date_format="iso")
    except Exception as exc:
        error_msg = f"Error fetching data: {exc}"
        logger.error(error_msg)
        return error_msg

if __name__ == "__main__":
    app.run(transport="stdio")