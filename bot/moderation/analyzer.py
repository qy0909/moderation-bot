from .sentiment import analyze_sentiment, normalize_sentiment
from .toxicity import analyze_toxicity
from .fallback_model import fallback_sentiment, fallback_toxicity


def analyze_text(text):
    # PRIMARY: API
    sentiment = analyze_sentiment(text)
    toxicity = analyze_toxicity(text)

    # FALLBACK
    if sentiment["polarity"] == "UNKNOWN":
        sentiment = fallback_sentiment(text)

    if toxicity["label"] == "unknown":
        toxicity = fallback_toxicity(text)

    # NORMALIZE AFTER FINAL RESULT
    sentiment_score = normalize_sentiment(sentiment)

    return {
        "text": text,
        "sentiment_confidence": sentiment["confidence"],
        "sentiment": sentiment_score,
        "sentiment_label": sentiment["polarity"],
        "toxicity": toxicity["score"],
        "toxicity_label": toxicity["label"],
        "severity": toxicity.get("severity", "non-toxic")
    }