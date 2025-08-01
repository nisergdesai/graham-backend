from yfinance_fetcher import get_yf_data
from marketwatch_scraper import get_eps_history, check_dividends_stable
import math
import numpy as np

def human_readable_number(num):
    if num is None or (isinstance(num, float) and math.isnan(num)):
        return "N/A"
    abs_num = abs(num)
    if abs_num >= 1_000_000_000:
        return f"{num / 1_000_000_000:.2f}B"
    elif abs_num >= 1_000_000:
        return f"{num / 1_000_000:.2f}M"
    elif abs_num >= 1_000:
        return f"{num / 1_000:.2f}K"
    return f"{num:.2f}"

def to_native(value):
    """Convert numpy types to native Python types"""
    if isinstance(value, np.generic):
        return value.item()
    return value

def convert_numpy(obj):
    """Recursively convert numpy data to native Python types"""
    if isinstance(obj, dict):
        return {k: convert_numpy(v) for k, v in obj.items()}
    elif isinstance(obj, tuple):
        return tuple(convert_numpy(x) for x in obj)
    elif isinstance(obj, list):
        return [convert_numpy(x) for x in obj]
    elif isinstance(obj, np.generic):
        return obj.item()
    return obj

def evaluate_stock(ticker):
    yf_data = get_yf_data(ticker)
    eps_history = get_eps_history(ticker)

    results = {}

    # Current Ratio
    cr = 0
    if yf_data["current_liabilities"]:
        cr = yf_data["current_assets"] / yf_data["current_liabilities"]
    results["Current Ratio ≥ 2"] = (round(cr, 2), to_native(cr >= 2))

    # Long-term Debt vs Net Current Assets
    ltd = yf_data.get("long_term_debt")
    if ltd is None or (isinstance(ltd, float) and math.isnan(ltd)):
        ltd = 0.0
    nca = yf_data["current_assets"] - yf_data["current_liabilities"]
    ltd_pass = ltd <= nca
    results["Long-term Debt ≤ Net Current Assets"] = (
        f"LTD: {human_readable_number(ltd)}, NCA: {human_readable_number(nca)}", to_native(ltd_pass)
    )

    # EPS Growth and Stability (5 years)
    min_years = 5
    required_growth = 0.145

    if len(eps_history) >= min_years:
        eps_oldest = eps_history[0]
        eps_newest = eps_history[min_years - 1]

        print(f"EPS History for {ticker} (oldest → newest): {eps_history[:min_years]}")
        print(f"Calculating EPS growth: eps_oldest={eps_oldest}, eps_newest={eps_newest}")

        if eps_oldest == 0:
            growth = None
        else:
            growth = (eps_newest - eps_oldest) / abs(eps_oldest)

        if growth is None:
            results["EPS Growth ≥ 14.5% in 5 years"] = ("N/A", False)
        else:
            results["EPS Growth ≥ 14.5% in 5 years"] = (f"{growth:.1%}", to_native(growth >= required_growth))
    else:
        results["EPS Growth ≥ 14.5% in 5 years"] = ("N/A (Insufficient EPS history)", False)

    # Positive EPS for 5 years — return array AND pass/fail bool
    if len(eps_history) >= min_years:
        last_5_eps = eps_history[:min_years]
        positive_eps = all(eps >= 0 for eps in last_5_eps)
    else:
        last_5_eps = []
        positive_eps = False
    results["Positive EPS for 5 years"] = (last_5_eps, to_native(positive_eps))

    # Dividend consistency (20-year record)
    dividends_ok = check_dividends_stable(ticker)
    results["20-Year Dividend Record"] = (to_native(dividends_ok), to_native(dividends_ok))

    # P/E Ratio
    pe = yf_data.get("trailing_pe")
    pe_pass = pe is not None and pe <= 15
    results["P/E ≤ 15"] = (round(pe, 2) if pe else "N/A", to_native(pe_pass))

    # P/B and PE×PB Test
    pb = None
    pe_pb_product = None
    if yf_data.get("book_value_per_share") and yf_data.get("price"):
        pb = yf_data["price"] / yf_data["book_value_per_share"]
    if pe and pb:
        pe_pb_product = pe * pb
        pb_pass = pb <= 1.5
        product_pass = pe_pb_product <= 22.5
        combined_pass = pb_pass or product_pass
        results["P/B ≤ 1.5 or PE×PB ≤ 22.5"] = (
            f"P/B: {pb:.2f}, PE×PB: {pe_pb_product:.2f}", to_native(combined_pass)
        )
    else:
        results["P/B ≤ 1.5 or PE×PB ≤ 22.5"] = ("N/A (missing PE or BVPS)", False)

    return convert_numpy(results)
