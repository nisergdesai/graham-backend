import yfinance as yf

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
