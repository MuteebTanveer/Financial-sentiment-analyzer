"""Score each article, then combine them into one verdict.

FinBERT (a model trained on financial news) is used when HF_API_TOKEN is set.
Otherwise VADER runs locally with extra finance vocabulary.
"""

import math
import os
from datetime import datetime, timezone

import requests
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

HF_URL = os.getenv("HF_API_URL", "https://router.huggingface.co/hf-inference/models/ProsusAI/finbert")

# VADER does not know market language: "shares fall 5%" scores neutral by default.
# Values use VADER's -4..4 scale.
FINANCE_LEXICON = {
    "bullish": 2.5, "bearish": -2.5, "rally": 2.0, "rallies": 2.0, "rallied": 2.0,
    "surge": 2.0, "surges": 2.0, "surged": 2.0, "soar": 2.5, "soars": 2.5, "soared": 2.5,
    "jump": 1.5, "jumps": 1.5, "jumped": 1.5, "climb": 1.3, "climbs": 1.3, "climbed": 1.3,
    "rise": 1.2, "rises": 1.2, "rose": 1.2, "gain": 1.5, "gains": 1.5, "gained": 1.5,
    "rebound": 1.5, "rebounds": 1.5, "recover": 1.3, "recovers": 1.3,
    "beat": 1.5, "beats": 1.5, "tops": 1.2, "upgrade": 2.0, "upgraded": 2.0, "upgrades": 2.0,
    "outperform": 2.0, "outperforms": 2.0, "inflows": 1.2, "buyback": 1.2, "approval": 1.5,
    "breakout": 1.8, "uptrend": 1.8, "all-time": 0.8, "dividend": 0.8, "profit": 1.5,
    "plunge": -2.5, "plunges": -2.5, "plunged": -2.5, "tumble": -2.2, "tumbles": -2.2,
    "tumbled": -2.2, "slump": -2.2, "slumps": -2.2, "slumped": -2.2, "sink": -1.8,
    "sinks": -1.8, "sank": -1.8, "fall": -1.5, "falls": -1.5, "fell": -1.5, "drop": -1.5,
    "drops": -1.5, "dropped": -1.5, "decline": -1.5, "declines": -1.5, "declined": -1.5,
    "slide": -1.5, "slides": -1.5, "slid": -1.5, "dip": -1.0, "dips": -1.0, "miss": -1.5,
    "misses": -1.5, "missed": -1.5, "downgrade": -2.0, "downgraded": -2.0, "downgrades": -2.0,
    "underperform": -2.0, "selloff": -2.2, "sell-off": -2.2, "crash": -3.0, "crashes": -3.0,
    "lawsuit": -1.5, "probe": -1.2, "layoffs": -1.8, "bankruptcy": -3.0, "recession": -2.2,
    "hack": -2.5, "hacked": -2.5, "exploit": -2.0, "liquidation": -2.0, "liquidations": -2.0,
    "outflows": -1.2, "downtrend": -1.8, "losses": -1.8, "loss": -1.5, "warning": -1.3,
    "volatile": -0.5, "fraud": -3.0, "investigation": -1.3, "recall": -1.5, "tariffs": -1.0,
}

_vader = SentimentIntensityAnalyzer()
_vader.lexicon.update(FINANCE_LEXICON)


def model_name():
    return "FinBERT" if os.getenv("HF_API_TOKEN") else "VADER"


def _text(art, limit=480):
    text = art["headline"]
    if art["summary"]:
        text += ". " + art["summary"]
    return text[:limit]


def _vader_score(art):
    # Feed raw text: VADER uses capitals, "!" and negation, so cleaning hurts it.
    head = _vader.polarity_scores(art["headline"])["compound"]
    if not art["summary"]:
        return head
    body = _vader.polarity_scores(art["summary"][:600])["compound"]
    return 0.65 * head + 0.35 * body


def _finbert_scores(articles):
    """One batched call. Score = P(positive) - P(negative)."""
    res = requests.post(
        HF_URL,
        headers={"Authorization": f"Bearer {os.environ['HF_API_TOKEN']}"},
        json={"inputs": [_text(a) for a in articles], "options": {"wait_for_model": True}},
        timeout=25,
    )
    res.raise_for_status()
    data = res.json()
    if not isinstance(data, list) or len(data) != len(articles):
        raise ValueError("unexpected FinBERT response")
    scores = []
    for row in data:
        row = row if isinstance(row, list) else [row]
        probs = {d["label"].lower(): d["score"] for d in row}
        scores.append(probs.get("positive", 0) - probs.get("negative", 0))
    return scores


def score_articles(articles):
    """Adds 'score' (-1..1) to each article. Returns the model actually used."""
    used = "VADER"
    scores = None
    if os.getenv("HF_API_TOKEN") and articles:
        try:
            scores = _finbert_scores(articles)
            used = "FinBERT"
        except Exception:
            scores = None  # fall back quietly so the site still answers
    if scores is None:
        scores = [_vader_score(a) for a in articles]
    for art, s in zip(articles, scores):
        art["score"] = max(-1.0, min(1.0, s))
    return used


def label_for(score, model):
    cut = 0.2 if model == "FinBERT" else 0.1
    if score >= cut:
        return "positive"
    if score <= -cut:
        return "negative"
    return "neutral"


def aggregate(articles, days, model):
    """Weighted mean where newer and more relevant stories count more."""
    now = datetime.now(timezone.utc)
    half_life = 2.0 if days <= 7 else 7.0  # days
    total_w = total_ws = total_abs = sum_sq = 0.0
    counts = {"positive": 0, "neutral": 0, "negative": 0}
    for art in articles:
        age = max(0.0, (now - art["published"]).total_seconds() / 86400)
        w = art["relevance"] * math.pow(0.5, age / half_life)
        w *= 1 + 0.15 * min(len(art["also_in"]), 4)  # widely reported stories matter more
        art["weight"] = w
        art["label"] = label_for(art["score"], model)
        counts[art["label"]] += 1
        total_w += w
        total_ws += w * art["score"]
        total_abs += w * abs(art["score"])
        sum_sq += w * w

    mean = total_ws / total_w if total_w else 0.0
    score = round(mean * 100)

    if score >= 8:
        verdict = "BULLISH"
    elif score <= -8:
        verdict = "BEARISH"
    else:
        verdict = "NEUTRAL"

    # Confidence: how many stories (effective count) and how much they agree.
    n_eff = (total_w ** 2 / sum_sq) if sum_sq else 0
    agreement = abs(total_ws) / total_abs if total_abs else 0
    if verdict == "NEUTRAL":
        agreement = 1 - agreement  # for neutral, mixed or flat news supports the call
    volume = min(1.0, n_eff / 12) ** 0.5
    confidence = round(100 * volume * (0.35 + 0.65 * agreement))
    conf_label = "High" if confidence >= 65 else "Medium" if confidence >= 40 else "Low"

    return {
        "score": score,
        "verdict": verdict,
        "confidence": confidence,
        "confidence_label": conf_label,
        "breakdown": counts,
    }


def by_source(articles):
    groups = {}
    for art in articles:
        g = groups.setdefault(art["source"], {"source": art["source"], "count": 0, "sum": 0.0})
        g["count"] += 1
        g["sum"] += art["score"]
    rows = [
        {"source": g["source"], "count": g["count"], "score": round(100 * g["sum"] / g["count"])}
        for g in groups.values()
    ]
    return sorted(rows, key=lambda r: -r["count"])[:8]
