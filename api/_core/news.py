"""Fetch news from Finnhub, GNews and NewsAPI, then filter and deduplicate."""

import os
import re
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

import requests

from .assets import term_pattern

TIMEOUT = 8
FINNHUB = "https://finnhub.io/api/v1"


def _key(name):
    return os.getenv(name) or None


def enabled_sources():
    keys = {"Finnhub": "FINNHUB_API_KEY", "GNews": "GNEWS_API_KEY", "NewsAPI": "NEWS_API_KEY"}
    return [name for name, env in keys.items() if _key(env)]


def _iso(dt):
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse_iso(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)
    except ValueError:
        return None


def _article(headline, summary, source, url, published, provider, from_company_feed=False):
    return {
        "headline": (headline or "").strip(),
        "summary": (summary or "").strip(),
        "source": (source or provider).strip(),
        "url": url or "",
        "published": published,
        "provider": provider,
        "company_feed": from_company_feed,
    }


def _get(url, params):
    res = requests.get(url, params=params, timeout=TIMEOUT)
    res.raise_for_status()
    return res.json()


# ---------- sources ----------

def fetch_finnhub(asset, since):
    key = _key("FINNHUB_API_KEY")
    if not key:
        return []
    out = []
    if asset.get("company"):
        data = _get(f"{FINNHUB}/company-news", {
            "symbol": asset["company"],
            "from": since.strftime("%Y-%m-%d"),
            "to": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "token": key,
        })
        company_feed = True
    else:
        # crypto and commodities have no company feed, use the general feeds
        category = "crypto" if asset.get("kind") == "crypto" else "general"
        data = _get(f"{FINNHUB}/news", {"category": category, "token": key})
        company_feed = False
    for item in data if isinstance(data, list) else []:
        published = datetime.fromtimestamp(item.get("datetime", 0), tz=timezone.utc)
        if published < since:
            continue
        out.append(_article(item.get("headline"), item.get("summary"), item.get("source"),
                            item.get("url"), published, "Finnhub", company_feed))
    return out[:60]


def fetch_gnews(asset, since):
    key = _key("GNEWS_API_KEY")
    if not key:
        return []
    data = _get("https://gnews.io/api/v4/search", {
        "q": asset["query"], "from": _iso(since), "sortby": "publishedAt",
        "lang": "en", "max": 25, "apikey": key,
    })
    return [
        _article(i.get("title"), i.get("description"), (i.get("source") or {}).get("name"),
                 i.get("url"), _parse_iso(i.get("publishedAt")), "GNews")
        for i in data.get("articles", [])
    ]


def fetch_newsapi(asset, since):
    key = _key("NEWS_API_KEY")
    if not key:
        return []
    data = _get("https://newsapi.org/v2/everything", {
        "q": asset["query"], "from": _iso(since), "sortBy": "publishedAt",
        "language": "en", "searchIn": "title,description", "pageSize": 30, "apiKey": key,
    })
    if data.get("status") != "ok":
        return []
    return [
        _article(i.get("title"), i.get("description"), (i.get("source") or {}).get("name"),
                 i.get("url"), _parse_iso(i.get("publishedAt")), "NewsAPI")
        for i in data.get("articles", [])
        if i.get("title") and i.get("title") != "[Removed]"
    ]


# ---------- cleaning ----------

_WORD = re.compile(r"[a-z0-9]+")


def _tokens(text):
    return set(_WORD.findall(text.lower()))


def _similar(a, b):
    if not a or not b:
        return False
    return len(a & b) / len(a | b) >= 0.6


def relevance(article, pattern):
    """1.0 if the headline names the asset, 0.6 if only the summary does,
    0.4 for company-feed items that name it nowhere, 0 otherwise."""
    if pattern.search(article["headline"]):
        return 1.0
    if pattern.search(article["summary"]):
        return 0.6
    if article["company_feed"]:
        return 0.4
    return 0.0


def dedupe(articles):
    """Same story syndicated across outlets should count once."""
    kept = []
    for art in sorted(articles, key=lambda a: a["published"]):
        toks = _tokens(art["headline"])
        dup = next((k for k in kept if _similar(toks, k["_tokens"])), None)
        if dup:
            dup["also_in"].add(art["source"])
            if len(art["summary"]) > len(dup["summary"]):
                dup["summary"] = art["summary"]
            continue
        art["_tokens"] = toks
        art["also_in"] = set()
        kept.append(art)
    for art in kept:
        art.pop("_tokens")
        art["also_in"] = sorted(art["also_in"] - {art["source"]})
    return kept


def fetch_news(asset, days):
    """Returns (articles, errors). Each article has a relevance weight."""
    since = datetime.now(timezone.utc) - timedelta(days=days)
    fetchers = {"Finnhub": fetch_finnhub, "GNews": fetch_gnews, "NewsAPI": fetch_newsapi}
    raw, errors = [], []
    with ThreadPoolExecutor(max_workers=3) as pool:
        futures = {name: pool.submit(fn, asset, since) for name, fn in fetchers.items()}
        for name, fut in futures.items():
            try:
                raw.extend(fut.result())
            except Exception as exc:  # one source failing should not kill the request
                errors.append(f"{name}: {type(exc).__name__}")

    pattern = term_pattern(asset["terms"])
    relevant = []
    for art in raw:
        if not art["headline"] or not art["published"] or art["published"] < since:
            continue
        rel = relevance(art, pattern)
        if rel > 0:
            art["relevance"] = rel
            relevant.append(art)
    return dedupe(relevant), errors


# ---------- price ----------

def fetch_quote(asset):
    key = _key("FINNHUB_API_KEY")
    symbol = asset.get("quote")
    if not key or not symbol:
        return None
    try:
        data = _get(f"{FINNHUB}/quote", {"symbol": symbol, "token": key})
    except Exception:
        return None
    if not data or not data.get("c"):
        return None
    return {
        "symbol": symbol,
        "note": asset.get("quote_note"),
        "price": data["c"],
        "change": data.get("d"),
        "change_pct": data.get("dp"),
    }


def fetch_profile(symbol):
    """Company profile for custom tickers. None if the symbol is unknown."""
    key = _key("FINNHUB_API_KEY")
    if not key:
        return None
    try:
        data = _get(f"{FINNHUB}/stock/profile2", {"symbol": symbol, "token": key})
    except Exception:
        return None
    return data if data and data.get("name") else None
