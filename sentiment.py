# ============================================
# SENTIMENT ANALYSIS PIPELINE
# Production version - called by FastAPI
# ============================================

import re
import pandas as pd
import nltk
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

# Download required NLTK data
nltk.download("punkt",     quiet=True)
nltk.download("punkt_tab", quiet=True)
nltk.download("stopwords", quiet=True)
nltk.download("wordnet",   quiet=True)

# Initialize tools once (not inside function for performance)
analyzer   = SentimentIntensityAnalyzer()
lemmatizer = WordNetLemmatizer()
stop_words = set(stopwords.words("english"))

# ============================================
# STEP 1: CLEAN TEXT
# Lowercase, remove URLs, symbols, whitespace
# ============================================
def clean_text(text):
    if pd.isna(text) or text is None:
        return ""
    text = text.lower()
    text = re.sub(r"http\S+|www\S+", "", text)
    text = re.sub(r"[^a-z\s]", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text

# ============================================
# STEP 2: TOKENIZE
# Split text into individual words
# ============================================
def tokenize(text):
    return word_tokenize(text)

# ============================================
# STEP 3: REMOVE STOPWORDS
# Remove words with no sentiment value
# ============================================
def remove_stopwords(tokens):
    return [w for w in tokens if w not in stop_words]

# ============================================
# STEP 4: LEMMATIZE
# Reduce words to base form
# surging → surge, crashed → crash
# ============================================
def lemmatize(tokens):
    return [lemmatizer.lemmatize(w) for w in tokens]

# ============================================
# MAIN PIPELINE FUNCTION
# Called by FastAPI with asset + articles
# Returns verdict + score
# ============================================
def run_sentiment_pipeline(asset, articles):

    # Load articles into DataFrame
    df = pd.DataFrame(articles)

    if df.empty:
        return {"verdict": "NEUTRAL", "score": 0}

    # Filter relevant articles by asset keyword
    keyword = asset.lower()
    mask = (
        df["headline"].str.lower().str.contains(keyword, na=False) |
        df["summary"].str.lower().str.contains(keyword, na=False)
    )
    df = df[mask].copy()

    if df.empty:
        return {"verdict": "NEUTRAL", "score": 0}

    # Remove duplicates
    df = df.drop_duplicates(subset=["headline"])

    # Clean text
    df["clean_headline"] = df["headline"].apply(clean_text)
    df["clean_summary"]  = df["summary"].apply(clean_text)
    df["full_text"]      = df["clean_headline"] + " " + df["clean_summary"]

    # Tokenize
    df["tokens"] = df["full_text"].apply(tokenize)

    # Remove stopwords
    df["tokens"] = df["tokens"].apply(remove_stopwords)

    # Lemmatize
    df["tokens"] = df["tokens"].apply(lemmatize)

    # Score with VADER
    df["compound"] = df["full_text"].apply(
        lambda x: analyzer.polarity_scores(x)["compound"]
    )

    # Aggregate scores
    avg_score   = df["compound"].mean()
    final_score = round(avg_score * 100)

    # Final verdict
    if avg_score >= 0.05:
        verdict = "BULLISH"
    elif avg_score <= -0.05:
        verdict = "BEARISH"
    else:
        verdict = "NEUTRAL"

    return {
        "verdict": verdict,
        "score":   final_score
    }