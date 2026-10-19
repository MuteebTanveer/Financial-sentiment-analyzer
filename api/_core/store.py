"""Result cache and daily history.

Uses Postgres when DATABASE_URL (or POSTGRES_URL from Vercel's Neon integration)
is set. Without it, falls back to memory, which works but forgets on cold starts.
"""

import json
import os
import threading
from datetime import date, datetime, timedelta, timezone

DB_URL = os.getenv("DATABASE_URL") or os.getenv("POSTGRES_URL")

SCHEMA = """
CREATE TABLE IF NOT EXISTS sentiment_snapshots (
    asset        TEXT        NOT NULL,
    period       TEXT        NOT NULL,
    day          DATE        NOT NULL,
    score        INTEGER     NOT NULL,
    verdict      TEXT        NOT NULL,
    confidence   INTEGER     NOT NULL,
    payload      JSONB       NOT NULL,
    analyzed_at  TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (asset, period, day)
);
"""


def _today():
    return datetime.now(timezone.utc).date()


class MemoryStore:
    def __init__(self):
        self.rows = {}  # (asset, period, day) -> dict
        self.lock = threading.Lock()

    def get_fresh(self, asset, period, max_age):
        row = self.rows.get((asset, period, _today()))
        if row and datetime.now(timezone.utc) - row["analyzed_at"] < max_age:
            return row["payload"]
        return None

    def save(self, asset, period, payload):
        with self.lock:
            self.rows[(asset, period, _today())] = {
                "score": payload["score"], "verdict": payload["verdict"],
                "payload": payload, "analyzed_at": datetime.now(timezone.utc),
            }

    def history(self, asset, period, days):
        start = _today() - timedelta(days=days)
        out = [
            {"date": d.isoformat(), "score": r["score"], "verdict": r["verdict"]}
            for (a, p, d), r in self.rows.items() if a == asset and p == period and d >= start
        ]
        return sorted(out, key=lambda r: r["date"])


class PostgresStore:
    def __init__(self, url):
        import psycopg  # imported here so the app runs without it locally
        self.psycopg = psycopg
        self.url = url
        with self._conn() as conn:
            conn.execute(SCHEMA)

    def _conn(self):
        return self.psycopg.connect(self.url, autocommit=True, connect_timeout=5)

    def get_fresh(self, asset, period, max_age):
        with self._conn() as conn:
            row = conn.execute(
                "SELECT payload FROM sentiment_snapshots "
                "WHERE asset=%s AND period=%s AND day=%s AND analyzed_at > %s",
                (asset, period, _today(), datetime.now(timezone.utc) - max_age),
            ).fetchone()
        return row[0] if row else None

    def save(self, asset, period, payload):
        with self._conn() as conn:
            conn.execute(
                """INSERT INTO sentiment_snapshots
                   (asset, period, day, score, verdict, confidence, payload, analyzed_at)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,now())
                   ON CONFLICT (asset, period, day) DO UPDATE SET
                     score=EXCLUDED.score, verdict=EXCLUDED.verdict,
                     confidence=EXCLUDED.confidence, payload=EXCLUDED.payload,
                     analyzed_at=now()""",
                (asset, period, _today(), payload["score"], payload["verdict"],
                 payload["confidence"], json.dumps(payload)),
            )

    def history(self, asset, period, days):
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT day, score, verdict FROM sentiment_snapshots "
                "WHERE asset=%s AND period=%s AND day >= %s ORDER BY day",
                (asset, period, _today() - timedelta(days=days)),
            ).fetchall()
        return [{"date": d.isoformat(), "score": s, "verdict": v} for d, s, v in rows]


def make_store():
    if DB_URL:
        try:
            return PostgresStore(DB_URL), True
        except Exception as exc:
            print(f"Database unavailable, using memory cache: {exc}")
    return MemoryStore(), False


def trend_from_history(history, score):
    """Compare today's score with the most recent earlier day."""
    today = _today().isoformat()
    earlier = [h for h in history if h["date"] < today]
    if not earlier:
        return {"trend": "NEW", "change": 0, "previous": None,
                "message": "First reading. The trend shows from tomorrow onward."}
    prev = earlier[-1]
    change = score - prev["score"]
    when = "yesterday" if prev["date"] == (_today() - timedelta(days=1)).isoformat() \
        else date.fromisoformat(prev["date"]).strftime("%b %d")
    if change > 5:
        trend, msg = "IMPROVING", f"Up {change} points since {when}"
    elif change < -5:
        trend, msg = "DECLINING", f"Down {abs(change)} points since {when}"
    else:
        trend, msg = "STABLE", f"Roughly unchanged since {when} ({change:+d})"
    return {"trend": trend, "change": change, "previous": prev, "message": msg}
