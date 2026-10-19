# Market Mood

A financial news sentiment analyzer. Pick a coin, commodity or any US stock, and it reads the
latest news, scores every story, and tells you whether coverage leans bullish, bearish or
neutral. It also shows which stories drive the score, how confident it is, and how the mood has
moved day by day.

## How the score works

1. News comes from Finnhub, GNews and NewsAPI (whichever keys you set).
2. Only stories that actually name the asset are kept, matched as whole words, so "eth" never
   matches "method".
3. The same story from different outlets is merged into one.
4. Each story is scored from -100 to +100. With a Hugging Face token it uses FinBERT, a model
   trained on financial news. Without one it uses VADER with extra market vocabulary.
5. Stories are averaged with weights: newer stories, stories that name the asset in the
   headline, and stories reported by several outlets count more.
6. Confidence goes up with more stories and with stories that agree with each other.

## Run locally

```bash
# backend
pip install -r requirements.txt
cp .env.example .env        # add at least FINNHUB_API_KEY
uvicorn api.index:app --reload --port 8000

# frontend (second terminal)
cd sentiment_frontend/web_front
npm install
npm run dev                 # open http://localhost:5173
```

Without `DATABASE_URL` it keeps results in memory, which is fine for local use.

## Deploy on Vercel

1. Import this repo on vercel.com. Leave the root directory as the repo root; `vercel.json`
   handles the build.
2. Add environment variables (Settings, Environment Variables):
   - `FINNHUB_API_KEY` (required, free at finnhub.io)
   - `GNEWS_API_KEY` (recommended, free at gnews.io)
   - `HF_API_TOKEN` (recommended for accuracy, free read token at huggingface.co)
   - `DATABASE_URL` for history: add the Neon integration from the Vercel Storage tab and it
     sets `POSTGRES_URL` for you. The table is created on first run.
3. Deploy. The site and the API share one domain, so no CORS setup is needed.

NewsAPI's free plan only allows development use, so leave `NEWS_API_KEY` empty on the public
site unless you have a paid plan.

## API

- `GET /api/analyze?asset=BTC&period=7d` full report (period is `7d` or `30d`)
- `GET /api/health` which model, sources and database are active
- `GET /api/docs` interactive docs

## Disclaimer

This measures how the news sounds, not where prices will go. It is not financial advice.
