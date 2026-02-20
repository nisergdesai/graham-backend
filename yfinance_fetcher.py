import yfinance as yf
import math


def get_yf_data(ticker_symbol):
    ticker = yf.Ticker(ticker_symbol)
    bs = ticker.balance_sheet
    info = ticker.info

    # Helper to avoid KeyError if row is missing
    def safe_get(df, label):
        return df.loc[label].iloc[0] if label in df.index else 0

    return {
        "current_assets": safe_get(bs, "Current Assets"),
        "current_liabilities": safe_get(bs, "Current Liabilities"),
        "long_term_debt": safe_get(bs, "Long Term Debt"),
        "book_value_per_share": info.get("bookValue", None),
        "price": info.get("currentPrice", None),
        "trailing_pe": info.get("trailingPE", None),
        "eps_ttm": info.get("trailingEps", None),
    }


def get_eps_history(ticker_symbol):
    """
    Fetch annual EPS history from yfinance income statement.
    Returns a list of EPS values ordered oldest -> newest.
    Tries 'Basic EPS' first, then 'Diluted EPS'.
    """
    try:
        ticker = yf.Ticker(ticker_symbol)
        # .income_stmt gives annual data, columns are dates newest -> oldest
        inc = ticker.income_stmt

        if inc is None or inc.empty:
            print(f"No income statement data for {ticker_symbol}")
            return []

        # Try to find EPS row
        eps_row = None
        for label in ["Basic EPS", "Diluted EPS"]:
            if label in inc.index:
                eps_row = inc.loc[label]
                break

        if eps_row is None:
            print(f"No EPS row found in income statement for {ticker_symbol}")
            return []

        # eps_row is a Series with date columns, newest first -> reverse to oldest first
        eps_values = []
        for val in reversed(eps_row.values):
            if val is None or (isinstance(val, float) and math.isnan(val)):
                eps_values.append(0.0)
            else:
                eps_values.append(float(val))

        return eps_values

    except Exception as e:
        print(f"Error fetching EPS history for {ticker_symbol}: {e}")
        return []


def check_dividends_20yr(ticker_symbol):
    """
    Check if a stock has a 20-year dividend payment record using yfinance.
    Returns True if the stock has paid dividends spanning at least 20 years.
    """
    try:
        ticker = yf.Ticker(ticker_symbol)
        divs = ticker.dividends

        if divs is None or divs.empty:
            return False

        # divs.index is a DatetimeIndex of dividend payment dates
        earliest = divs.index.min()
        latest = divs.index.max()
        years_of_dividends = (latest - earliest).days / 365.25

        return years_of_dividends >= 20

    except Exception as e:
        print(f"Error fetching dividend history for {ticker_symbol}: {e}")
        return False
