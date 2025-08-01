import requests
from bs4 import BeautifulSoup

session = requests.Session()
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/114.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Referer": "https://www.marketwatch.com/",
    "Origin": "https://www.marketwatch.com",
}

def get_eps_history(ticker):
    url = f"https://www.marketwatch.com/investing/stock/{ticker}/financials"
    try:
        res = session.get(url, headers=HEADERS, timeout=10)
        res.raise_for_status()
    except Exception as e:
        print(f"Error fetching EPS data for {ticker}: {e}")
        return []

    soup = BeautifulSoup(res.text, "html.parser")

    for row in soup.select("table tbody tr"):
        if "eps" in row.text.lower():
            print(f"Found EPS row for {ticker}: {row.text.strip()[:100]}...")
            tds = row.find_all("td")[1:]  # skip label cell
            eps_values = []
            for td in tds:
                raw_text = td.text.strip().replace(",", "")
                # Handle parentheses as negative values
                if raw_text.startswith("(") and raw_text.endswith(")"):
                    cleaned_text = "-" + raw_text[1:-1]
                else:
                    cleaned_text = raw_text

                try:
                    val = float(cleaned_text) if cleaned_text else 0.0
                except ValueError:
                    val = 0.0
                eps_values.append(val)
            return eps_values

    print(f"EPS (Basic) row not found for {ticker}")
    return []

def check_dividends_stable(ticker):
    url = f"https://www.marketwatch.com/investing/stock/{ticker}/dividends"
    try:
        res = session.get(url, headers=HEADERS, timeout=10)
        res.raise_for_status()
    except Exception as e:
        print(f"Error fetching dividends data for {ticker}: {e}")
        return False

    soup = BeautifulSoup(res.text, "html.parser")

    dividends_table = soup.find("table", {"class": "table"})
    if dividends_table and "dividend" in dividends_table.text.lower():
        print(f"Dividends table found for {ticker}")
        return True

    if "dividends" in res.text.lower():
        print(f"Dividends keyword found on page for {ticker}")
        return True

    print(f"No dividend info found for {ticker}")
    return False
