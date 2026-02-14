from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from graham_checker import evaluate_stock
import traceback
import sys
import re

# Force unbuffered stdout so prints show in Render logs
import functools
print = functools.partial(print, flush=True)

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

# 
cache = {}  # Optional in-memory cache

@app.head("/")
def root_head():
    return {}

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
        tb = traceback.format_exc()
        print(f"[ERROR] /analyze failed for {ticker}:\n{tb}", flush=True)
        raise HTTPException(status_code=500, detail=f"Analysis failed for {ticker}: {str(e)}")

@app.get("/debug")
def debug(ticker: str = Query(..., min_length=1)):
    """Debug endpoint -- hit this in your browser to see full error details."""
    ticker = ticker.strip().upper()
    print(f"[DEBUG] Starting debug for {ticker}", flush=True)
    
    errors = []
    yf_data = None
    eps_data = None
    dividends = None
    
    # Step 1: yfinance data
    try:
        from yfinance_fetcher import get_yf_data
        yf_data = get_yf_data(ticker)
        print(f"[DEBUG] yf_data OK: {yf_data}", flush=True)
    except Exception as e:
        errors.append({"step": "yfinance_fetcher", "error": str(e), "traceback": traceback.format_exc()})
        print(f"[DEBUG] yf_data FAILED: {e}", flush=True)
    
    # Step 2: EPS history
    try:
        from marketwatch_scraper import get_eps_history
        eps_data = get_eps_history(ticker)
        print(f"[DEBUG] eps_data OK: {eps_data}", flush=True)
    except Exception as e:
        errors.append({"step": "get_eps_history", "error": str(e), "traceback": traceback.format_exc()})
        print(f"[DEBUG] eps_data FAILED: {e}", flush=True)

    # Step 3: Dividends
    try:
        from marketwatch_scraper import check_dividends_stable
        dividends = check_dividends_stable(ticker)
        print(f"[DEBUG] dividends OK: {dividends}", flush=True)
    except Exception as e:
        errors.append({"step": "check_dividends_stable", "error": str(e), "traceback": traceback.format_exc()})
        print(f"[DEBUG] dividends FAILED: {e}", flush=True)

    # Step 4: Full evaluation
    full_result = None
    try:
        full_result = evaluate_stock(ticker)
        print(f"[DEBUG] evaluate_stock OK", flush=True)
    except Exception as e:
        errors.append({"step": "evaluate_stock", "error": str(e), "traceback": traceback.format_exc()})
        print(f"[DEBUG] evaluate_stock FAILED: {e}", flush=True)

    return JSONResponse(content={
        "ticker": ticker,
        "yf_data": str(yf_data),
        "eps_data": str(eps_data),
        "dividends": str(dividends),
        "full_result": str(full_result),
        "errors": errors,
        "status": "all_ok" if not errors else "has_errors"
    })
