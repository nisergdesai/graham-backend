import yfinance as yf
import math
import numpy as np
import functools
print = functools.partial(print, flush=True)

def get_yf_data(ticker_symbol):
    try:
        ticker = yf.Ticker(ticker_symbol)
        bs = ticker.balance_sheet
        info = ticker.info

        if info is None or not info:
            raise ValueError(f"No info returned from yfinance for {ticker_symbol}. The ticker may be invalid.")

        def to_python(val):
            """Convert numpy/pandas types to native Python, handling NaN."""
            if val is None:
                return 0
            if isinstance(val, np.generic):
                val = val.item()
            if isinstance(val, float) and (math.isnan(val) or math.isinf(val)):
                return 0
            return val

        # Helper to avoid KeyError if row is missing
        def safe_get(df, label):
            if df is None or df.empty:
                return 0
            # Try exact match first, then case-insensitive search
            if label in df.index:
                return to_python(df.loc[label].iloc[0])
            # Try case-insensitive match
            for idx in df.index:
                if idx.lower().replace(" ", "") == label.lower().replace(" ", ""):
                    return to_python(df.loc[idx].iloc[0])
            return 0

        data = {
            "current_assets": safe_get(bs, "Current Assets"),
            "current_liabilities": safe_get(bs, "Current Liabilities"),
            "long_term_debt": safe_get(bs, "Long Term Debt"),
            "book_value_per_share": info.get("bookValue", None),
            "price": info.get("currentPrice", None),
            "trailing_pe": info.get("trailingPE", None),
            "eps_ttm": info.get("trailingEps", None),
        }

        print(f"[yfinance] Data for {ticker_symbol}: current_assets={data['current_assets']}, "
              f"current_liabilities={data['current_liabilities']}, long_term_debt={data['long_term_debt']}, "
              f"price={data['price']}, pe={data['trailing_pe']}, bvps={data['book_value_per_share']}")

        return data

    except Exception as e:
        print(f"[yfinance] ERROR fetching data for {ticker_symbol}: {e}")
        raise ValueError(f"Failed to fetch financial data for {ticker_symbol} from yfinance: {e}")
