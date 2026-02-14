import requests
from bs4 import BeautifulSoup
import yfinance as yf

session = requests.Session()
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/124.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Referer": "https://www.marketwatch.com/",
    "Origin": "https://www.marketwatch.com",
}


def get_eps_history_from_marketwatch(ticker):
    """Try to get EPS history from MarketWatch (may be blocked by bot detection)."""
    url = f"https://www.marketwatch.com/investing/stock/{ticker.lower()}/financials"
    try:
        res = session.get(url, headers=HEADERS, timeout=15)
        res.raise_for_status()
    except Exception as e:
        print(f"[MarketWatch] Error fetching EPS data for {ticker}: {e}")
        return None

    if res.status_code == 403 or "captcha" in res.text.lower() or "robot" in res.text.lower():
        print(f"[MarketWatch] Blocked by bot detection for {ticker}")
        return None

    soup = BeautifulSoup(res.text, "html.parser")

    for row in soup.select("table tbody tr"):
        row_text = row.text.lower()
        if "eps" in row_text and "basic" in row_text:
            print(f"[MarketWatch] Found EPS row for {ticker}: {row.text.strip()[:100]}...")
            tds = row.find_all("td")[1:]  # skip label cell
            eps_values = []
            for td in tds:
                raw_text = td.text.strip().replace(",", "")
                if raw_text.startswith("(") and raw_text.endswith(")"):
                    cleaned_text = "-" + raw_text[1:-1]
                else:
                    cleaned_text = raw_text
                try:
                    val = float(cleaned_text) if cleaned_text else 0.0
                except ValueError:
                    val = 0.0
                eps_values.append(val)
            if eps_values:
                return eps_values

    # Fallback: try any row with "eps" if "basic" match failed
    for row in soup.select("table tbody tr"):
        if "eps" in row.text.lower():
            print(f"[MarketWatch] Found EPS row (fallback) for {ticker}: {row.text.strip()[:100]}...")
            tds = row.find_all("td")[1:]
            eps_values = []
            for td in tds:
                raw_text = td.text.strip().replace(",", "")
                if raw_text.startswith("(") and raw_text.endswith(")"):
                    cleaned_text = "-" + raw_text[1:-1]
                else:
                    cleaned_text = raw_text
                try:
                    val = float(cleaned_text) if cleaned_text else 0.0
                except ValueError:
                    val = 0.0
                eps_values.append(val)
            if eps_values:
                return eps_values

    print(f"[MarketWatch] EPS row not found for {ticker}")
    return None


def get_eps_history_from_yfinance(ticker):
    """Fallback: get EPS history from yfinance earnings data."""
    try:
        t = yf.Ticker(ticker)
        # Try income statement for historical EPS
        income = t.income_stmt
        if income is not None and not income.empty:
            if "Basic EPS" in income.index:
                eps_row = income.loc["Basic EPS"]
            elif "Diluted EPS" in income.index:
                eps_row = income.loc["Diluted EPS"]
            else:
                print(f"[yfinance EPS] No EPS row in income statement for {ticker}")
                print(f"[yfinance EPS] Available rows: {list(income.index)[:20]}")
                return []

            # income_stmt columns are dates, most recent first - reverse for oldest first
            eps_values = []
            for val in reversed(eps_row.values):
                try:
                    eps_values.append(float(val))
                except (ValueError, TypeError):
                    eps_values.append(0.0)

            print(f"[yfinance EPS] EPS history for {ticker}: {eps_values}")
            return eps_values

        print(f"[yfinance EPS] No income statement data for {ticker}")
        return []

    except Exception as e:
        print(f"[yfinance EPS] Error getting EPS for {ticker}: {e}")
        return []


def get_eps_history(ticker):
    """Get EPS history, trying MarketWatch first, then falling back to yfinance."""
    # Try MarketWatch first
    eps = get_eps_history_from_marketwatch(ticker)
    if eps and len(eps) > 0:
        print(f"[EPS] Using MarketWatch data for {ticker}: {eps}")
        return eps

    # Fallback to yfinance
    print(f"[EPS] MarketWatch failed for {ticker}, falling back to yfinance...")
    eps = get_eps_history_from_yfinance(ticker)
    if eps and len(eps) > 0:
        print(f"[EPS] Using yfinance data for {ticker}: {eps}")
        return eps

    print(f"[EPS] No EPS data available for {ticker} from any source")
    return []


def check_dividends_stable(ticker):
    """Check dividend history using yfinance first (reliable), then MarketWatch fallback."""
    # Primary: use yfinance dividends
    try:
        t = yf.Ticker(ticker)
        dividends = t.dividends
        if dividends is not None and len(dividends) > 0:
            # Check if dividends span at least some years
            years_of_data = (dividends.index[-1] - dividends.index[0]).days / 365.25
            has_dividends = years_of_data >= 1 and len(dividends) >= 4
            print(f"[Dividends] yfinance: {ticker} has {len(dividends)} records over {years_of_data:.1f} years -> {'PASS' if has_dividends else 'FAIL'}")
            return has_dividends
    except Exception as e:
        print(f"[Dividends] yfinance error for {ticker}: {e}")

    # Fallback: MarketWatch
    url = f"https://www.marketwatch.com/investing/stock/{ticker.lower()}/dividends"
    try:
        res = session.get(url, headers=HEADERS, timeout=15)
        res.raise_for_status()
    except Exception as e:
        print(f"[Dividends] MarketWatch error for {ticker}: {e}")
        return False

    soup = BeautifulSoup(res.text, "html.parser")

    dividends_table = soup.find("table", {"class": "table"})
    if dividends_table and "dividend" in dividends_table.text.lower():
        print(f"[Dividends] MarketWatch: table found for {ticker}")
        return True

    if "dividends" in res.text.lower():
        print(f"[Dividends] MarketWatch: keyword found for {ticker}")
        return True

    print(f"[Dividends] No dividend info found for {ticker}")
    return False
