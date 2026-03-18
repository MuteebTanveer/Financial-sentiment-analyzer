import mysql.connector
from dotenv import load_dotenv
import os

load_dotenv()

def get_connection():
    return mysql.connector.connect(
        host=os.getenv("DB_HOST"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME"),
        use_pure=True
    )

def is_data_fresh(asset, period):
    conn   = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id FROM sentiment_results
        WHERE asset = %s
        AND period = %s
        AND analyzed_date = CURDATE()
    """, (asset, period))
    row = cursor.fetchone()
    cursor.close()
    conn.close()
    return row is not None

def get_today_result(asset, period):
    conn   = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT * FROM sentiment_results
        WHERE asset = %s
        AND period = %s
        AND analyzed_date = CURDATE()
    """, (asset, period))
    row = cursor.fetchone()
    cursor.close()
    conn.close()
    return row

def get_yesterday_result(asset, period):
    conn   = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT * FROM sentiment_results
        WHERE asset = %s
        AND period = %s
        AND analyzed_date = CURDATE() - INTERVAL 1 DAY
    """, (asset, period))
    row = cursor.fetchone()
    cursor.close()
    conn.close()
    return row

def get_history(asset, period):
    days   = 7 if period == "7d" else 30
    conn   = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT verdict, score, analyzed_date
        FROM sentiment_results
        WHERE asset = %s AND period = %s
        AND analyzed_date >= CURDATE() - INTERVAL %s DAY
        ORDER BY analyzed_date ASC
    """, (asset, period, days))
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return rows

def save_news(asset, articles):
    conn   = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM news_cache WHERE asset = %s", (asset,))
    for article in articles:
        cursor.execute("""
            INSERT INTO news_cache
            (asset, headline, summary, source, published_at, fetched_at, expires_at)
            VALUES (%s, %s, %s, %s, %s, NOW(), DATE_ADD(NOW(), INTERVAL 24 HOUR))
        """, (
            asset,
            article.get("headline"),
            article.get("summary"),
            article.get("source"),
            article.get("published_at")
        ))
    conn.commit()
    cursor.close()
    conn.close()

def save_sentiment(asset, period, verdict, score):
    conn   = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO sentiment_results
        (asset, period, verdict, score, analyzed_at, analyzed_date)
        VALUES (%s, %s, %s, %s, NOW(), CURDATE())
        ON DUPLICATE KEY UPDATE
            verdict     = VALUES(verdict),
            score       = VALUES(score),
            analyzed_at = NOW()
    """, (asset, period, verdict, score))
    conn.commit()
    cursor.close()
    conn.close()

def get_trend(today_score, yesterday_score):
    if yesterday_score is None:
        return {
            "trend":           "NEW",
            "change":          0,
            "message":         "First analysis — no previous data",
            "yesterday_score": None,
            "today_score":     today_score
        }

    change = today_score - yesterday_score

    if change > 5:
        trend   = "IMPROVING"
        message = f"Sentiment improving by {int(change)} points"
    elif change < -5:
        trend   = "DECLINING"
        message = f"Sentiment declining by {int(abs(change))} points"
    else:
        trend   = "STABLE"
        message = f"Sentiment stable ({int(change):+d} points)"

    return {
        "trend":           trend,
        "change":          int(change),
        "message":         message,
        "yesterday_score": float(yesterday_score),
        "today_score":     float(today_score)
    }