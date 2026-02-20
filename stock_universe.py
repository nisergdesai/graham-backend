import yfinance as yf
from yfinance import EquityQuery


def get_screener_candidates():
    """
    Use yfinance's built-in screener API to pre-filter US equities
    on the quantitative Graham criteria that map to available fields:
      - Current Ratio >= 2
      - P/E > 0 AND P/E <= 15
      - P/B <= 15 (relaxed from 1.5 to avoid missing PE*PB <= 22.5 stocks)

    Returns a list of ticker symbols that pass this initial screen.
    """

    query = EquityQuery("AND", [
        # Current Ratio >= 2
        EquityQuery("GTE", ["currentratio.lasttwelvemonths", 2]),
        # Positive P/E (profitable)
        EquityQuery("GT", ["peratio.lasttwelvemonths", 0]),
        # P/E <= 15
        EquityQuery("LTE", ["peratio.lasttwelvemonths", 15]),
        # P/B <= 15 (relaxed -- the detailed check will enforce P/B<=1.5 or PE*PB<=22.5)
        EquityQuery("LTE", ["pricebookratio.quarterly", 15]),
    ])

    all_tickers = []
    offset = 0
    page_size = 250  # max allowed by Yahoo Finance screener

    print("[Screener] Starting yfinance screener pre-filter...")

    while True:
        try:
            response = yf.screen(
                query,
                offset=offset,
                size=page_size,
            )
        except Exception as e:
            print(f"[Screener] Error at offset {offset}: {e}")
            break

        quotes = response.get("quotes", [])
        if not quotes:
            break

        batch_tickers = [q["symbol"] for q in quotes if "symbol" in q]
        all_tickers.extend(batch_tickers)

        total = response.get("total", 0)
        print(f"[Screener] Fetched {len(all_tickers)}/{total} candidates (offset={offset})")

        offset += page_size
        if offset >= total:
            break

    print(f"[Screener] Pre-filter complete: {len(all_tickers)} candidates found")
    return all_tickers
