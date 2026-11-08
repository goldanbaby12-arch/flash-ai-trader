import os
from typing import Optional

import httpx
import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

BINANCE_BASE = os.getenv("BINANCE_BASE_URL", "https://api.binance.com")
app = FastAPI(title="Flash AI Trader", version="0.1.0")
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def home():
    return FileResponse("static/index.html")

@app.get("/api/health")
async def health():
    return {"status": "ok", "app": "Flash AI Trader", "mode": "analysis-only"}

async def get_klines(symbol: str, interval: str, limit: int = 150):
    url = f"{BINANCE_BASE}/api/v3/klines"
    params = {"symbol": symbol.upper(), "interval": interval, "limit": limit}
    try:
        async with httpx.AsyncClient(timeout=12) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            raw = response.json()
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Binance market-data request failed: {exc}")
    if not isinstance(raw, list) or len(raw) < 60:
        raise HTTPException(status_code=422, detail="Not enough candle data for analysis.")
    df = pd.DataFrame(raw, columns=[
        "open_time","open","high","low","close","volume","close_time",
        "quote_volume","trades","taker_buy_base","taker_buy_quote","ignore"
    ])
    for col in ["open","high","low","close","volume"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    return df

def add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    close = df["close"]
    df["ema20"] = close.ewm(span=20, adjust=False).mean()
    df["ema50"] = close.ewm(span=50, adjust=False).mean()
    delta = close.diff()
    gain = delta.clip(lower=0).ewm(alpha=1/14, adjust=False).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1/14, adjust=False).mean()
    rs = gain / loss.replace(0, 1e-12)
    df["rsi"] = 100 - (100 / (1 + rs))
    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    df["macd"] = ema12 - ema26
    df["macd_signal"] = df["macd"].ewm(span=9, adjust=False).mean()
    tr = pd.concat([
        df["high"] - df["low"],
        (df["high"] - close.shift()).abs(),
        (df["low"] - close.shift()).abs()
    ], axis=1).max(axis=1)
    df["atr"] = tr.rolling(14).mean()
    return df

@app.get("/api/signal")
async def signal(
    symbol: str = Query("BTCUSDT", min_length=5, max_length=20),
    interval: str = Query("1h"),
):
    allowed = {"1m","3m","5m","15m","30m","1h","2h","4h","6h","8h","12h","1d","3d","1w"}
    if interval not in allowed:
        raise HTTPException(status_code=400, detail="Unsupported interval.")
    if not symbol.replace("USDT", "").isalnum() or not symbol.endswith("USDT"):
        raise HTTPException(status_code=400, detail="Use a Binance USDT pair, e.g. BTCUSDT.")
    df = add_indicators(await get_klines(symbol, interval))
    last = df.iloc[-1]
    price = float(last.close)
    rsi = float(last.rsi)
    ema20, ema50 = float(last.ema20), float(last.ema50)
    macd, macd_sig = float(last.macd), float(last.macd_signal)
    atr = float(last.atr) if pd.notna(last.atr) else price * 0.01

    direction = "NO TRADE"
    reasons = []
    if ema20 > ema50 and rsi >= 50 and rsi <= 70 and macd > macd_sig:
        direction = "LONG"
        reasons = ["EMA20 is above EMA50", "RSI confirms positive momentum", "MACD is above its signal line"]
    elif ema20 < ema50 and rsi >= 30 and rsi < 50 and macd < macd_sig:
        direction = "SHORT"
        reasons = ["EMA20 is below EMA50", "RSI confirms negative momentum", "MACD is below its signal line"]
    else:
        reasons = ["Trend and momentum conditions are not aligned; wait for confirmation"]

    entry = price
    stop = target1 = target2 = None
    risk_pct = None
    if direction == "LONG":
        stop = entry - 1.5 * atr
        risk = entry - stop
        target1, target2 = entry + risk, entry + 2 * risk
        risk_pct = (risk / entry) * 100
    elif direction == "SHORT":
        stop = entry + 1.5 * atr
        risk = stop - entry
        target1, target2 = entry - risk, entry - 2 * risk
        risk_pct = (risk / entry) * 100

    return {
        "symbol": symbol.upper(), "interval": interval, "signal": direction,
        "price": round(price, 8), "entry": round(entry, 8),
        "stop_loss": round(stop, 8) if stop is not None else None,
        "take_profit_1": round(target1, 8) if target1 is not None else None,
        "take_profit_2": round(target2, 8) if target2 is not None else None,
        "estimated_risk_percent": round(risk_pct, 3) if risk_pct is not None else None,
        "indicators": {"rsi14": round(rsi, 2), "ema20": round(ema20, 8),
                       "ema50": round(ema50, 8), "macd": round(macd, 8),
                       "macd_signal": round(macd_sig, 8), "atr14": round(atr, 8)},
        "reasons": reasons,
        "mode": "analysis-only",
        "warning": "Educational signal, not financial advice. SHORT is analytical only; no orders are placed."
    }
