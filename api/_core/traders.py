"""Trader mood: what traders say and how they are positioned.

Three kinds of signal, each optional so the app keeps working if one is blocked:
  crowd        posts from StockTwits (self-tagged Bullish/Bearish) and Reddit (needs keys)
  positioning  share of futures accounts that are long (Binance, OKX, Bybit or Gate)
  fear_greed   the Crypto Fear & Greed Index (crypto only)
"""

import math
import os
import re
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

import requests
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

from .sentiment import FINANCE_LEXICON

TIMEOUT = 7
UA = "MarketMood/1.0 (+https://github.com/MuteebTanveer/Financial-sentiment-analyzer)"
CROWD_HOURS = 72  # only recent chatter counts as current mood

# Trader slang VADER has never seen. Scale is -4..4.
SOCIAL_LEXICON = {
    **FINANCE_LEXICON,
    "moon": 2.5, "mooning": 2.8, "moonshot": 2.2, "pump": 1.5, "pumping": 1.8, "pumped": 1.5,
    "dump": -2.0, "dumping": -2.2, "dumped": -2.0, "rekt": -2.8, "rug": -3.0, "rugged": -3.0,
    "hodl": 1.0, "hodling": 1.0, "ath": 1.8, "lfg": 2.2, "wagmi": 2.0, "ngmi": -2.2,
    "bagholder": -1.8, "bagholders": -1.8, "bags": -0.8, "fud": -1.2, "fomo": 0.6,
    "capitulation": -2.4, "squeeze": 1.2, "calls": 1.2, "puts": -1.2, "shorting": -1.4,
    "shorted": -1.2, "longing": 1.2, "longed": 1.0, "bottomed": 1.4, "topped": -1.4,
    "buying": 0.6, "btfd": 1.8, "bullrun": 2.5, "parabolic": 1.8, "bleeding": -2.0,
    "tanking": -2.4, "tanked": -2.2, "ripping": 2.0, "send": 0.8, "sending": 1.2,
    "🚀": 2.5, "🌙": 2.0, "📈": 1.8, "📉": -1.8, "🐻": -1.6, "🐂": 1.6, "💎": 1.0,
}
_vader = SentimentIntensityAnalyzer()
_vader.lexicon.update(SOCIAL_LEXICON)

_URL = re.compile(r"https?://\S+")
_CASHTAG = re.compile(r"\$[A-Za-z.]{1,10}")


def _get(url, params=None, headers=None):
    res = requests.get(url, params=params, headers={"User-Agent": UA, **(headers or {})}, timeout=TIMEOUT)
    res.raise_for_status()
    return res.json()


def _clean(text):
    text = _URL.sub("", text or "")
    text = _CASHTAG.sub("", text)
    return re.sub(r"\s+", " ", text).strip()


def text_score(text):
    return _vader.polarity_scores(_clean(text))["compound"]


# ---------------- crowd: StockTwits ----------------

def fetch_stocktwits(asset):
    sym = asset.get("twits")
    if not sym:
        return []
    data = _get(f"https://api.stocktwits.com/api/2/streams/symbol/{sym}.json")
    posts = []
    for m in data.get("messages", []):
        tag = ((m.get("entities") or {}).get("sentiment") or {}).get("basic")
        body = m.get("body") or ""
        if tag == "Bullish":
            score, tagged = 0.8, True
        elif tag == "Bearish":
            score, tagged = -0.8, True
        else:
            score, tagged = text_score(body) * 0.7, False  # untagged text is a weaker signal
        user = m.get("user") or {}
        posts.append({
            "text": body[:400],
            "source": "StockTwits",
            "url": f"https://stocktwits.com/{user.get('username', '')}/message/{m.get('id')}",
            "created": m.get("created_at"),
            "score": score,
            "tagged": tagged,
            "likes": ((m.get("likes") or {}).get("total")) or 0,
        })
    return posts


# ---------------- crowd: Reddit (optional, needs approved OAuth app) ----------------

_reddit_token = {"value": None, "expires": 0}


def _reddit_auth():
    cid, secret = os.getenv("REDDIT_CLIENT_ID"), os.getenv("REDDIT_CLIENT_SECRET")
    if not cid or not secret:
        return None
    if _reddit_token["value"] and time.time() < _reddit_token["expires"] - 60:
        return _reddit_token["value"]
    res = requests.post(
        "https://www.reddit.com/api/v1/access_token",
        auth=(cid, secret), data={"grant_type": "client_credentials"},
        headers={"User-Agent": UA}, timeout=TIMEOUT,
    )
    res.raise_for_status()
    body = res.json()
    _reddit_token.update(value=body["access_token"], expires=time.time() + body.get("expires_in", 3600))
    return _reddit_token["value"]


def fetch_reddit(asset):
    token = _reddit_auth()
    if not token or not asset.get("subs"):
        return []
    query = " OR ".join(f'"{t}"' for t in asset["terms"][:3])
    data = _get(
        f"https://oauth.reddit.com/r/{'+'.join(asset['subs'])}/search",
        params={"q": query, "restrict_sr": 1, "sort": "new", "t": "week", "limit": 100},
        headers={"Authorization": f"Bearer {token}"},
    )
    posts = []
    for child in data.get("data", {}).get("children", []):
        d = child.get("data", {})
        text = (d.get("title") or "") + ". " + (d.get("selftext") or "")[:500]
        posts.append({
            "text": (d.get("title") or "")[:300],
            "source": f"r/{d.get('subreddit')}",
            "url": "https://www.reddit.com" + (d.get("permalink") or ""),
            "created": datetime.fromtimestamp(d.get("created_utc", 0), tz=timezone.utc).isoformat(),
            "score": text_score(text),
            "tagged": False,
            "likes": max(0, d.get("score") or 0),
        })
    return posts


def crowd(asset):
    """Returns (summary or None, posts, errors)."""
    posts, errors, used = [], [], []
    fetchers = {"StockTwits": fetch_stocktwits, "Reddit": fetch_reddit}
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = {name: pool.submit(fn, asset) for name, fn in fetchers.items()}
        for name, fut in futures.items():
            try:
                got = fut.result()
                if got:
                    used.append(name)
                posts.extend(got)
            except Exception as exc:
                errors.append(f"{name}: {_reason(exc)}")

    cutoff = datetime.now(timezone.utc) - timedelta(hours=CROWD_HOURS)
    fresh = []
    for p in posts:
        try:
            created = datetime.fromisoformat(str(p["created"]).replace("Z", "+00:00"))
        except ValueError:
            continue
        if created >= cutoff:
            p["created"] = created.strftime("%Y-%m-%dT%H:%M:%SZ")
            fresh.append(p)
    if not fresh:
        return None, [], errors

    total_w = total = 0.0
    bull = bear = 0
    for p in fresh:
        # liked posts and posts where the author picked a side count more
        w = (1 + math.log1p(p["likes"])) * (1.5 if p["tagged"] else 1.0)
        p["weight"] = round(w, 3)
        total_w += w
        total += w * p["score"]
        if p["score"] >= 0.1:
            p["label"], bull = "positive", bull + 1
        elif p["score"] <= -0.1:
            p["label"], bear = "negative", bear + 1
        else:
            p["label"] = "neutral"
        p["score"] = round(p["score"] * 100)

    summary = {
        "score": round(100 * total / total_w),
        "posts": len(fresh),
        "bullish": bull,
        "bearish": bear,
        "tagged": sum(1 for p in fresh if p["tagged"]),
        "sources": used,
    }
    fresh.sort(key=lambda p: p["created"], reverse=True)
    return summary, fresh[:40], errors


# ---------------- positioning: long/short account ratio ----------------

def _binance(coin):
    rows = _get("https://fapi.binance.com/futures/data/globalLongShortAccountRatio",
                {"symbol": f"{coin}USDT", "period": "1h", "limit": 25})
    return float(rows[-1]["longAccount"]), float(rows[0]["longAccount"])


def _okx(coin):
    data = _get("https://www.okx.com/api/v5/rubik/stat/contracts/long-short-account-ratio",
                {"ccy": coin, "period": "1H"})["data"]  # newest first, [ts, long/short]
    now, before = float(data[0][1]), float(data[min(24, len(data) - 1)][1])
    return now / (1 + now), before / (1 + before)


def _bybit(coin):
    rows = _get("https://api.bybit.com/v5/market/account-ratio",
                {"category": "linear", "symbol": f"{coin}USDT", "period": "1h", "limit": 25})["result"]["list"]
    return float(rows[0]["buyRatio"]), float(rows[-1]["buyRatio"])  # newest first


def _gate(coin):
    rows = _get("https://api.gateio.ws/api/v4/futures/usdt/contract_stats",
                {"contract": f"{coin}_USDT", "interval": "1h", "limit": 25})
    rows = sorted(rows, key=lambda r: r["time"])
    now, before = float(rows[-1]["lsr_account"]), float(rows[0]["lsr_account"])
    return now / (1 + now), before / (1 + before)


EXCHANGES = [("Binance", _binance), ("OKX", _okx), ("Bybit", _bybit), ("Gate", _gate)]


def positioning(asset):
    coin = asset.get("perp")
    if not coin:
        return None, []
    errors = []
    for name, fn in EXCHANGES:
        try:
            now, before = fn(coin)
        except Exception as exc:
            errors.append(f"{name}: {_reason(exc)}")
            continue
        if not 0 < now < 1:
            continue
        long_pct = round(now * 100, 1)
        return {
            "exchange": name,
            "long_pct": long_pct,
            "long_pct_24h": round(before * 100, 1),
            # 50% long is neutral; 75% long reads as +50
            "score": max(-100, min(100, round((long_pct - 50) * 2))),
        }, errors
    return None, errors


# ---------------- crypto fear & greed ----------------

def fear_greed(asset):
    if asset.get("kind") != "crypto":
        return None, []
    try:
        data = _get("https://api.alternative.me/fng/", {"limit": 2})["data"]
    except Exception as exc:
        return None, [f"Fear & Greed: {_reason(exc)}"]
    v = int(data[0]["value"])
    return {
        "value": v,
        "label": data[0]["value_classification"],
        "yesterday": int(data[1]["value"]) if len(data) > 1 else None,
        "score": (v - 50) * 2,
    }, []


def _reason(exc):
    if isinstance(exc, requests.HTTPError) and exc.response is not None:
        return f"HTTP {exc.response.status_code}"
    return type(exc).__name__


# ---------------- combine ----------------

WEIGHTS = {"crowd": 0.45, "positioning": 0.35, "fear_greed": 0.20}


def analyze(asset):
    with ThreadPoolExecutor(max_workers=3) as pool:
        f_crowd = pool.submit(crowd, asset)
        f_pos = pool.submit(positioning, asset)
        f_fg = pool.submit(fear_greed, asset)
        crowd_sum, posts, e1 = f_crowd.result()
        pos, e2 = f_pos.result()
        fg, e3 = f_fg.result()

    parts = {"crowd": crowd_sum, "positioning": pos, "fear_greed": fg}
    w_total = s_total = 0.0
    for key, part in parts.items():
        if not part:
            continue
        w = WEIGHTS[key]
        if key == "crowd" and part["posts"] < 10:
            w *= part["posts"] / 10  # a handful of posts shouldn't dominate
        w_total += w
        s_total += w * part["score"]

    if not w_total:
        return None, e1 + e2 + e3

    score = round(s_total / w_total)
    verdict = "BULLISH" if score >= 8 else "BEARISH" if score <= -8 else "NEUTRAL"
    signals = sum(1 for p in parts.values() if p)
    return {
        "score": score,
        "verdict": verdict,
        "signals": signals,
        "crowd": crowd_sum,
        "positioning": pos,
        "fear_greed": fg,
        "posts": posts,
        "source_errors": e1 + e2 + e3,
        "analyzed_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }, e1 + e2 + e3
