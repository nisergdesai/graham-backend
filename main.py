from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from graham_checker import evaluate_stock, safe_evaluate_stock, passes_mandatory_criteria
from stock_universe import get_screener_candidates
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
import re

app = FastAPI(title="Graham Stock Screener API")

# Add BOTH localhost and Vercel for development + production
origins = [
    "http://localhost:3000",
    "https://graham-frontend.vercel.app"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,         # This MUST match your frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

cache = {}  # Single-ticker analysis cache
screen_cache = {
    "results": None,
    "timestamp": None,
    "running": False,
}

MAX_WORKERS = 10          # concurrent threads for Phase 2 evaluation
BATCH_DELAY = 0.5         # seconds to wait between batches to avoid rate limits

@app.get("/")
def root():
    return {"message": "Welcome to the Graham Stock Screener API"}

@app.get("/analyze")
def analyze(ticker: str = Query(..., min_length=1, description="Stock ticker symbol (e.g., AAPL)")):
    ticker = ticker.strip().upper()

    if ' ' in ticker or len(ticker) > 10:
        raise HTTPException(status_code=400, detail="Ticker seems malformed.")

    if ticker in cache:
        return {"ticker": ticker, "graham_results": cache[ticker], "cached": True}

    try:
        results = evaluate_stock(ticker)
        cache[ticker] = results
        return {"ticker": ticker, "graham_results": results, "cached": False}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/screen")
def screen_stocks(refresh: bool = Query(False, description="Force a fresh scan instead of returning cached results")):
    """
    Scan all US-listed stocks and return those passing the 4 mandatory Graham criteria.
    All 7 criteria are shown for every passing stock.

    Phase 1: Pre-filter via yfinance screener API (fast, seconds).
    Phase 2: Detailed evaluation of candidates in parallel (minutes).

    Results are cached in memory. Pass ?refresh=true to force a re-scan.
    """

    # Return cached results if available and not forcing refresh
    if not refresh and screen_cache["results"] is not None:
        return {
            "cached": True,
            "cached_at": screen_cache["timestamp"],
            **screen_cache["results"],
        }

    # Prevent concurrent runs
    if screen_cache["running"]:
        raise HTTPException(
            status_code=409,
            detail="A screening run is already in progress. Try again later or use ?refresh=false to get cached results.",
        )

    screen_cache["running"] = True
    start_time = time.time()

    try:
        # ------- Phase 1: Pre-filter via yfinance screener -------
        candidates = get_screener_candidates()

        if not candidates:
            screen_cache["running"] = False
            return {
                "cached": False,
                "total_candidates": 0,
                "total_passed": 0,
                "stocks": [],
                "duration_seconds": round(time.time() - start_time, 1),
            }

        # ------- Phase 2: Detailed evaluation in parallel -------
        passing_stocks = []
        evaluated_count = 0
        error_count = 0

        print(f"[Screen] Starting Phase 2: evaluating {len(candidates)} candidates with {MAX_WORKERS} workers...")

        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            # Submit all candidate tickers for evaluation
            future_to_ticker = {
                executor.submit(safe_evaluate_stock, ticker): ticker
                for ticker in candidates
            }

            for future in as_completed(future_to_ticker):
                ticker, results = future.result()
                evaluated_count += 1

                if results is None:
                    error_count += 1
                    continue

                # Check the 4 mandatory criteria
                if passes_mandatory_criteria(results):
                    # Build structured output with all 7 criteria
                    criteria_output = {}
                    for criterion_name, (value, passed) in results.items():
                        criteria_output[criterion_name] = {
                            "value": value,
                            "passed": passed,
                        }
                    passing_stocks.append({
                        "ticker": ticker,
                        "criteria": criteria_output,
                    })

                # Log progress every 50 stocks
                if evaluated_count % 50 == 0:
                    print(f"[Screen] Progress: {evaluated_count}/{len(candidates)} evaluated, {len(passing_stocks)} passing so far")

        # Sort passing stocks alphabetically by ticker
        passing_stocks.sort(key=lambda s: s["ticker"])

        duration = round(time.time() - start_time, 1)
        print(f"[Screen] Complete: {evaluated_count} evaluated, {error_count} errors, {len(passing_stocks)} passed in {duration}s")

        result = {
            "total_candidates": len(candidates),
            "total_evaluated": evaluated_count,
            "total_errors": error_count,
            "total_passed": len(passing_stocks),
            "duration_seconds": duration,
            "stocks": passing_stocks,
        }

        # Cache the results
        screen_cache["results"] = result
        screen_cache["timestamp"] = time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())

        return {"cached": False, **result}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Screening failed: {str(e)}")

    finally:
        screen_cache["running"] = False
