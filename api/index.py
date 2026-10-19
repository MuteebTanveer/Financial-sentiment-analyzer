"""FastAPI app. Vercel serves this file as a Python function under /api."""

import os
import sys
import threading
import time
from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv  # noqa: E402

load_dotenv()

from fastapi import FastAPI, HTTPException, Query, Request  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402

from _core import news, sentiment, traders  # noqa: E402
from _core.assets import PRESETS, SYMBOL_RE, build_custom  # noqa: E402
from _core.store import make_store, trend_from_history  # noqa: E402

PERIODS = {"7d": 7, "30d": 30}
CACHE_AGE = timedelta(minutes=int(os.getenv("CACHE_MINUTES", "120")))
TRADER_AGE = timedelta(minutes=int(os.getenv("TRADER_CACHE_MINUTES", "30")))
FRESH_LIMIT = int(os.getenv("RATE_LIMIT_PER_MINUTE", "8"))  # new analyses per IP per minute

app = FastAPI(title="Market Mood API", docs_url="/api/docs", openapi_url="/api/openapi.json")

origins = [o.strip() for o in os.getenv("ALLOWED_ORIGINS", "").split(",") if o.strip()]
origins += ["http://localhost:5173", "http://127.0.0.1:5173"]
app.add_middleware(CORSMiddleware, allow_origins=origins, allow_methods=["GET"], allow_headers=["*"])

_store = None
_db_ok = False
_store_lock = threading.Lock()


def store():
    global _store, _db_ok
    with _store_lock:
        if _store is None:
            _store, _db_ok = make_store()
    return _store


# ---------- tiny per-IP rate limiter (per instance, good enough with the cache) ----------
_hits = defaultdict(deque)


def check_rate(ip):
    now = time.monotonic()
    q = _hits[ip]
    while q and now - q[0] > 60:
        q.popleft()
    if len(q) >= FRESH_LIMIT:
        raise HTTPException(429, "Too many new analyses from your connection. Try again in a minute.")
    q.append(now)


def client_ip(request):
    fwd = request.headers.get("x-forwarded-for", "")
    return fwd.split(",")[0].strip() or (request.client.host if request.client else "unknown")


# ---------- price cache (prices change faster than sentiment) ----------
_quotes = {}


def quote_for(symbol, asset):
    hit = _quotes.get(symbol)
    if hit and time.monotonic() - hit[0] < 60:
        return hit[1]
    q = news.fetch_quote(asset)
    _quotes[symbol] = (time.monotonic(), q)
    return q


def resolve_asset(symbol):
    if symbol in PRESETS:
        return PRESETS[symbol]
    profile = news.fetch_profile(symbol)
    if not profile:
        raise HTTPException(404, f"{symbol} isn't a ticker we can find. Try a US stock symbol like MSFT.")
    return build_custom(symbol, profile)


def public_article(a):
    return {
        "headline": a["headline"],
        "summary": a["summary"][:280],
        "source": a["source"],
        "also_in": a["also_in"],
        "url": a["url"],
        "published": a["published"].strftime("%Y-%m-%dT%H:%M:%SZ"),
        "score": round(a["score"] * 100),
        "label": a["label"],
        "weight": round(a["weight"], 3),
    }


def run_analysis(symbol, asset, period):
    days = PERIODS[period]
    articles, errors = news.fetch_news(asset, days)
    if not articles:
        detail = f"No recent news mentions {asset['name']} in the last {days} days."
        if errors and len(errors) == len(news.enabled_sources()):
            detail = "News sources aren't responding right now. Try again shortly."
        raise HTTPException(404, detail)

    model = sentiment.score_articles(articles)
    summary = sentiment.aggregate(articles, days, model)
    articles.sort(key=lambda a: a["published"], reverse=True)

    return {
        "asset": symbol,
        "name": asset["name"],
        "kind": asset["kind"],
        "period": period,
        **summary,
        "model": model,
        "article_count": len(articles),
        "sources": sentiment.by_source(articles),
        "articles": [public_article(a) for a in articles[:40]],
        "source_errors": errors,
        "analyzed_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }


@app.get("/api/health")
def health(request: Request, probe: bool = False):
    store()
    out = {
        "ok": True,
        "model": sentiment.model_name(),
        "database": _db_ok,
        "sources": news.enabled_sources(),
        "reddit": bool(os.getenv("REDDIT_CLIENT_ID")),
        "region": os.getenv("VERCEL_REGION"),
    }
    if probe:  # checks which trader data sources this server can reach
        check_rate(client_ip(request))
        btc = PRESETS["BTC"]
        checks = {}
        for name, fn in traders.EXCHANGES:
            try:
                fn("BTC")
                checks[name] = "ok"
            except Exception as exc:
                checks[name] = traders._reason(exc)
        for name, fn in [("StockTwits", traders.fetch_stocktwits), ("Fear & Greed", traders.fear_greed)]:
            try:
                got = fn(btc)
                checks[name] = "ok" if got and got[0] else "empty"
            except Exception as exc:
                checks[name] = traders._reason(exc)
        out["probe"] = checks
    return out


@app.get("/api/assets")
def assets():
    return [{"symbol": k, "name": v["name"], "kind": v["kind"]} for k, v in PRESETS.items()]


def check_symbol(asset):
    symbol = asset.upper().strip().lstrip("$")
    if not SYMBOL_RE.match(symbol):
        raise HTTPException(400, "Use a ticker symbol made of letters and numbers, like AAPL.")
    return symbol


@app.get("/api/traders")
def trader_mood(request: Request, asset: str = Query(..., min_length=1, max_length=10)):
    symbol = check_symbol(asset)
    db = store()
    payload = db.get_fresh(symbol, "traders", TRADER_AGE)
    cached = payload is not None
    if not cached:
        check_rate(client_ip(request))
        asset_cfg = resolve_asset(symbol)
        payload, errors = traders.analyze(asset_cfg)
        if payload is None:
            raise HTTPException(503, f"Trader data for {asset_cfg['name']} isn't reachable right now. Try again later.")
        payload.update(asset=symbol, name=asset_cfg["name"], kind=asset_cfg["kind"], confidence=0)
        db.save(symbol, "traders", payload)
    history = db.history(symbol, "traders", 30)
    return {**payload, "cached": cached, "history": history}


@app.get("/api/analyze")
def analyze(
    request: Request,
    asset: str = Query(..., min_length=1, max_length=10),
    period: str = Query("7d"),
):
    symbol = check_symbol(asset)
    if period not in PERIODS:
        raise HTTPException(400, "Period must be 7d or 30d.")
    if not news.enabled_sources():
        raise HTTPException(503, "No news API keys are configured on the server.")

    db = store()
    payload = db.get_fresh(symbol, period, CACHE_AGE)
    cached = payload is not None
    if not cached:
        check_rate(client_ip(request))
        asset_cfg = resolve_asset(symbol)
        payload = run_analysis(symbol, asset_cfg, period)
        db.save(symbol, period, payload)
    else:
        asset_cfg = PRESETS.get(symbol) or {"quote": symbol, "kind": payload.get("kind")}

    history = db.history(symbol, period, 30)
    return {
        **payload,
        "cached": cached,
        "history": history,
        **trend_from_history(history, payload["score"]),
        "price": quote_for(symbol, asset_cfg),
    }
