import requests
from dotenv import load_dotenv
import os
from datetime import datetime, timedelta

load_dotenv()

NEWS_API_KEY    = os.getenv("NEWS_API_KEY")
FINNHUB_API_KEY = os.getenv("FINNHUB_API_KEY")
GNEWS_API_KEY   = os.getenv("GNEWS_API_KEY")

def fetch_newsapi(asset, period):
    days      = 7 if period == "7d" else 30
    from_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    url       = "https://newsapi.org/v2/everything"
    params    = {
        "q":        asset,
        "from":     from_date,
        "sortBy":   "publishedAt",
        "language": "en",
        "pageSize": 20,
        "apiKey":   NEWS_API_KEY
    }
    try:
        res = requests.get(url, params=params, timeout=10)
        data = res.json()
        if data.get("status") != "ok":
            return []
        articles = []
        for item in data.get("articles", []):
            articles.append({
                "headline":     item.get("title", ""),
                "summary":      item.get("description", ""),
                "source":       item.get("source", {}).get("name", ""),
                "published_at": item.get("publishedAt", "")[:19].replace("T", " ")
            })
        return articles
    except:
        return []

def fetch_finnhub(asset, period):
    days      = 7 if period == "7d" else 30
    from_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    to_date   = datetime.now().strftime("%Y-%m-%d")
    url       = "https://finnhub.io/api/v1/company-news"
    params    = {
        "symbol": asset,
        "from":   from_date,
        "to":     to_date,
        "token":  FINNHUB_API_KEY
    }
    try:
        res = requests.get(url, params=params, timeout=10)
        data = res.json()
        if not isinstance(data, list):
            return []
        articles = []
        for item in data[:20]:
            articles.append({
                "headline":     item.get("headline", ""),
                "summary":      item.get("summary", ""),
                "source":       item.get("source", "Finnhub"),
                "published_at": datetime.fromtimestamp(
                    item.get("datetime", 0)
                ).strftime("%Y-%m-%d %H:%M:%S")
            })
        return articles
    except:
        return []

def fetch_gnews(asset, period):
    days      = 7 if period == "7d" else 30
    from_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%SZ")
    url       = "https://gnews.io/api/v4/search"
    params    = {
        "q":       asset,
        "from":    from_date,
        "sortby":  "publishedAt",
        "lang":    "en",
        "max":     20,
        "apikey":  GNEWS_API_KEY
    }
    try:
        res = requests.get(url, params=params, timeout=10)
        data = res.json()
        articles = []
        for item in data.get("articles", []):
            articles.append({
                "headline":     item.get("title", ""),
                "summary":      item.get("description", ""),
                "source":       item.get("source", {}).get("name", ""),
                "published_at": item.get("publishedAt", "")[:19].replace("T", " ")
            })
        return articles
    except:
        return []

def fetch_news(asset, period):
    """
    Fetch from all sources and combine
    More sources = better sentiment accuracy
    """
    print(f"Fetching news for {asset} ({period})...")

    newsapi_articles  = fetch_newsapi(asset, period)
    finnhub_articles  = fetch_finnhub(asset, period)
    gnews_articles    = fetch_gnews(asset, period)

    print(f"NewsAPI:  {len(newsapi_articles)} articles")
    print(f"Finnhub:  {len(finnhub_articles)} articles")
    print(f"GNews:    {len(gnews_articles)} articles")

    # Combine all sources
    all_articles = newsapi_articles + finnhub_articles + gnews_articles

    print(f"Total:    {len(all_articles)} articles")

    return all_articles