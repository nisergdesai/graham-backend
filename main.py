from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from graham_checker import evaluate_stock
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

# 
cache = {}  # Optional in-memory cache

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
