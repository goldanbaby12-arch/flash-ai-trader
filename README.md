# Flash AI Trader — MVP

A mobile-friendly, analysis-only crypto dashboard using public Binance market data.

## Features
- Binance public klines (no API key required)
- EMA 20/50, RSI 14, MACD, ATR
- LONG / SHORT / NO TRADE heuristic signals
- ATR-based illustrative stop-loss and targets
- FastAPI backend and responsive web dashboard

## Important limitations
- This is a prototype, not a profitable or validated strategy.
- It does not place orders, hold funds, or connect to a Binance account.
- SHORT is an analytical signal only. This prototype uses public spot candles.
- No LLM is connected yet. The first version uses transparent indicator rules; AI explanations can be added after testing.
- Always backtest and paper trade. Never commit API secrets to GitHub.

## Run locally (Android Termux or computer)
```bash
pkg update -y
pkg install python git -y
git clone YOUR_GITHUB_REPOSITORY_URL
cd flash-ai-trader
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000
```
Open `http://127.0.0.1:8000`.

## Deploy on Render from Android
1. Extract this ZIP.
2. Create a GitHub repository named `flash-ai-trader`.
3. Upload all extracted files and folders to the repository root.
4. In Render, create **New + → Blueprint** and connect that GitHub repository.
5. Render reads `render.yaml`; deploy the `flash-ai-trader` web service.
6. Open the generated `https://....onrender.com` URL.
7. Check `/api/health` and the dashboard.

If Blueprint deployment is unavailable, create a Web Service manually:
- Build command: `pip install -r requirements.txt`
- Start command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
- Health check path: `/api/health`

## Next development milestones
1. Persistent paper-trade ledger and portfolio simulation.
2. Historical backtesting with fees and slippage.
3. Multi-timeframe confirmation and signal confidence calibration.
4. Optional LLM-generated explanations with strict structured output.
5. Alerts and user authentication.
6. Only after extensive validation: a separate, explicitly enabled Binance execution service with restricted API permissions, withdrawal disabled, IP restrictions, position limits, and a kill switch.
