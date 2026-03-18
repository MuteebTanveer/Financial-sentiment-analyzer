from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database import (
    is_data_fresh,
    get_today_result,
    get_yesterday_result,
    get_history,
    save_news,
    save_sentiment,
    get_trend
)
from news_fetcher import fetch_news
from sentiment import run_sentiment_pipeline

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)

def build_response(asset, period, today, trend, history):
    yesterday = trend.get("yesterday_score")
    return {
        "source":           "cache" if today else "api",
        "asset":            asset,
        "period":           period,
        "verdict":          today["verdict"],
        "score":            today["score"],
        "analyzed_at":      str(today["analyzed_at"]),
        "trend":            trend["trend"],
        "trend_change":     trend["change"],
        "trend_message":    trend["message"],
        "yesterday_score":  yesterday,
        "history":          [
            {
                "date":    str(row["analyzed_date"]),
                "score":   row["score"],
                "verdict": row["verdict"]
            }
            for row in history
        ]
    }

@app.get("/analyze")
def analyze(asset: str, period: str):
    asset = asset.upper().strip()

    # Step 1 — Check if today's result already exists
    if is_data_fresh(asset, period):

        # Fetch from DB
        today     = get_today_result(asset, period)
        yesterday = get_yesterday_result(asset, period)
        history   = get_history(asset, period)

        # Compare with yesterday
        trend = get_trend(
            today["score"],
            yesterday["score"] if yesterday else None
        )

        return build_response(asset, period, today, trend, history)

    # Step 2 — No record for today, fetch fresh news
    articles = fetch_news(asset, period)

    if not articles:
        return {"error": "No news found for this asset"}

    # Step 3 — Save raw news to DB
    save_news(asset, articles)

    # Step 4 — Run sentiment pipeline
    result = run_sentiment_pipeline(asset, articles)

    # Step 5 — Save today's result to DB
    save_sentiment(
        asset=asset,
        period=period,
        verdict=result["verdict"],
        score=result["score"]
    )

    # Step 6 — Get yesterday for comparison
    today     = get_today_result(asset, period)
    yesterday = get_yesterday_result(asset, period)
    history   = get_history(asset, period)

    # Step 7 — Compare trend
    trend = get_trend(
        today["score"],
        yesterday["score"] if yesterday else None
    )

    return build_response(asset, period, today, trend, history)