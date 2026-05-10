from .sentiment import analyze_sentiment, normalize_sentiment
from .toxicity import analyze_toxicity
from .fallback_model import fallback_emotion, fallback_sentiment, fallback_toxicity
from .emotion import analyze_emotion


def analyze_text(text):
    # PRIMARY: API
    sentiment = analyze_sentiment(text)
    toxicity = analyze_toxicity(text)
    emotion = analyze_emotion(text)

    # FALLBACK
    if sentiment["polarity"] == "UNKNOWN":
        sentiment = fallback_sentiment(text)

    if toxicity["label"] == "unknown":
        toxicity = fallback_toxicity(text)

    if emotion["emotion"] == "unknown":
        emotion = fallback_emotion(text)

    # NORMALIZE AFTER FINAL RESULT
    sentiment_score = normalize_sentiment(sentiment)

    return {
        "text": text,
        "sentiment_confidence": sentiment["confidence"],
        "sentiment": sentiment_score,
        "sentiment_label": sentiment["polarity"],
        "toxicity": toxicity["score"],
        "toxicity_label": toxicity["label"],
        "severity": toxicity.get("severity", "non-toxic"),
        "emotion": emotion["emotion"],
        "emotion_confidence": emotion["confidence"]
    }