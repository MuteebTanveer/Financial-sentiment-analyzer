"""Asset definitions: how each symbol is searched, matched and priced."""

import re

# terms: words that must appear in an article for it to count as relevant
# query: what we send to the news search APIs
# company: symbol for Finnhub company news (stocks only)
# quote: symbol for the Finnhub price quote (ETFs stand in for gold, oil, S&P)
PRESETS = {
    "BTC":  {"name": "Bitcoin",  "kind": "crypto", "query": "bitcoin",
             "terms": ["bitcoin", "btc"], "quote": "BINANCE:BTCUSDT"},
    "ETH":  {"name": "Ethereum", "kind": "crypto", "query": "ethereum",
             "terms": ["ethereum", "ether", "eth"], "quote": "BINANCE:ETHUSDT"},
    "SOL":  {"name": "Solana",   "kind": "crypto", "query": "solana",
             "terms": ["solana"], "quote": "BINANCE:SOLUSDT"},
    "DOGE": {"name": "Dogecoin", "kind": "crypto", "query": "dogecoin",
             "terms": ["dogecoin", "doge"], "quote": "BINANCE:DOGEUSDT"},
    "GOLD": {"name": "Gold",     "kind": "commodity", "query": "gold price",
             "terms": ["gold", "bullion"], "quote": "GLD", "quote_note": "via GLD ETF"},
    "OIL":  {"name": "Crude oil", "kind": "commodity", "query": "crude oil",
             "terms": ["oil", "crude", "brent", "wti", "opec"], "quote": "USO",
             "quote_note": "via USO ETF"},
    "AAPL": {"name": "Apple",    "kind": "stock", "query": "Apple stock",
             "terms": ["apple", "aapl", "iphone"], "company": "AAPL", "quote": "AAPL"},
    "NVDA": {"name": "Nvidia",   "kind": "stock", "query": "Nvidia",
             "terms": ["nvidia", "nvda"], "company": "NVDA", "quote": "NVDA"},
    "TSLA": {"name": "Tesla",    "kind": "stock", "query": "Tesla stock",
             "terms": ["tesla", "tsla"], "company": "TSLA", "quote": "TSLA"},
    "SPX":  {"name": "S&P 500",  "kind": "index", "query": "S&P 500",
             "terms": ["s&p 500", "s&p500", "sp500", "wall street", "stocks"],
             "quote": "SPY", "quote_note": "via SPY ETF"},
}

SYMBOL_RE = re.compile(r"^[A-Z][A-Z0-9.\-]{0,9}$")

_SUFFIXES = re.compile(
    r"[,.]?\s+(inc|incorporated|corp|corporation|co|company|ltd|plc|holdings|group|class [a-z])\.?$",
    re.I,
)


def clean_company_name(name):
    name = name.strip()
    for _ in range(3):
        name = _SUFFIXES.sub("", name).strip()
    return name


def build_custom(symbol, profile):
    """Build an asset config for any stock ticker using its Finnhub profile."""
    name = clean_company_name(profile.get("name") or "") or symbol
    terms = [symbol.lower()]
    if name.lower() != symbol.lower():
        terms.append(name.lower())
    return {
        "name": name,
        "kind": "stock",
        "query": f"{name} stock" if name != symbol else symbol,
        "terms": terms,
        "company": symbol,
        "quote": symbol,
    }


def term_pattern(terms):
    """One regex that matches any term as a whole word (so 'eth' never hits 'method')."""
    parts = [re.escape(t) for t in sorted(terms, key=len, reverse=True)]
    return re.compile(r"(?<![a-z0-9])(" + "|".join(parts) + r")(?![a-z0-9])", re.I)
