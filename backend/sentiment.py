"""
Sentiment scoring engine — rule-based NLP for financial news.

Extracted from agents.py for modularity and testability.
"""
from __future__ import annotations

import re
from datetime import UTC, datetime, timedelta

from stock_data import SOURCE_QUALITY_WEIGHTS


# ─── Sentiment Term Weights ──────────────────────────────────────────────────

POSITIVE_TERM_WEIGHTS: dict[str, float] = {
    "gain": 0.9, "gains": 0.9, "rise": 0.85, "rises": 0.85,
    "up": 0.5, "surge": 1.5, "surges": 1.5, "jump": 1.2, "jumps": 1.2,
    "beats": 1.0, "beat": 1.0, "strong": 0.8, "profit": 1.1, "profits": 1.1,
    "growth": 1.0, "bullish": 1.2, "buy": 1.0, "record": 1.2,
    "expands": 0.8, "expansion": 0.8, "outperform": 1.1, "outperforms": 1.1,
    "upgrade": 1.1, "upgrades": 1.1,
}

NEGATIVE_TERM_WEIGHTS: dict[str, float] = {
    "fall": 0.9, "falls": 0.9, "down": 0.5, "drop": 1.0, "drops": 1.0,
    "slump": 1.4, "slumps": 1.4, "miss": 1.1, "misses": 1.1,
    "weak": 0.8, "loss": 1.2, "losses": 1.2, "decline": 1.0, "declines": 1.0,
    "bearish": 1.2, "sell": 1.0, "cuts": 0.9, "cut": 0.9, "risk": 0.9,
    "downgrade": 1.2, "downgrades": 1.2, "plunge": 1.7, "plunges": 1.7,
}

INTENSIFIER_WEIGHTS: dict[str, float] = {
    "marginal": 0.65, "slight": 0.7, "slightly": 0.7, "modest": 0.8,
    "moderate": 0.9, "solid": 1.1, "strong": 1.2, "sharp": 1.3,
    "significant": 1.35, "substantial": 1.45, "massive": 1.6, "huge": 1.6,
    "record": 1.5, "extreme": 1.7,
}

NEGATION_TERMS = {"no", "not", "never", "without", "hardly", "barely"}
CONTRAST_TERMS = {"but", "however", "despite", "although", "though", "yet"}


# ─── Core Scoring ────────────────────────────────────────────────────────────

def _clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


def _extract_numeric_magnitude_factor(text: str) -> float:
    percent_values = [
        float(match.group(1))
        for match in re.finditer(r"\b([0-9]+(?:\.[0-9]+)?)\s*%", text)
    ]
    if not percent_values:
        return 1.0
    peak = max(percent_values)
    if peak >= 100:
        return 1.6
    if peak >= 50:
        return 1.4
    if peak >= 20:
        return 1.25
    if peak >= 10:
        return 1.15
    return 1.0


def _score_segment(segment_text: str) -> tuple[float, float]:
    tokens = re.findall(r"[a-z]+", segment_text.lower())
    if not tokens:
        return 0.0, 0.0

    weighted_score = 0.0
    absolute_weight = 0.0

    for idx, token in enumerate(tokens):
        base_weight = 0.0
        if token in POSITIVE_TERM_WEIGHTS:
            base_weight = POSITIVE_TERM_WEIGHTS[token]
        elif token in NEGATIVE_TERM_WEIGHTS:
            base_weight = -NEGATIVE_TERM_WEIGHTS[token]
        else:
            continue

        lookback = tokens[max(0, idx - 3) : idx]

        intensity_factor = 1.0
        for prev_token in lookback:
            if prev_token in INTENSIFIER_WEIGHTS:
                intensity_factor *= INTENSIFIER_WEIGHTS[prev_token]

        if any(prev_token in NEGATION_TERMS for prev_token in lookback):
            base_weight *= -1

        contribution = base_weight * intensity_factor
        weighted_score += contribution
        absolute_weight += abs(contribution)

    magnitude_factor = _extract_numeric_magnitude_factor(segment_text)
    weighted_score *= magnitude_factor
    absolute_weight *= max(1.0, magnitude_factor * 0.9)

    return weighted_score, absolute_weight


def compute_sentiment(text: str) -> float:
    """Compute sentiment score for a piece of text. Returns float in [-1, 1]."""
    lowered = (text or "").lower()
    if not lowered.strip():
        return 0.0

    segments = re.split(r"(?i)\b(?:but|however|despite|although|though|yet)\b", lowered)
    segment_scores = []
    segment_weights = []

    for segment in segments:
        score, magnitude = _score_segment(segment)
        if magnitude <= 0:
            continue
        segment_scores.append(score)
        segment_weights.append(magnitude)

    if not segment_scores:
        return 0.0

    final_score = 0.0
    total_weight = 0.0
    segment_count = len(segment_scores)
    for idx, score in enumerate(segment_scores):
        recency_boost = 1.0 + (0.2 if idx == segment_count - 1 and segment_count > 1 else 0.0)
        weight = segment_weights[idx] * recency_boost
        final_score += score * recency_boost
        total_weight += weight

    if total_weight <= 0:
        return 0.0

    normalized = final_score / total_weight
    return _clamp(normalized, -1.0, 1.0)


# ─── Aggregate Sentiment Functions ───────────────────────────────────────────

def parse_datetime_text(value: str) -> datetime | None:
    """Parse various date formats commonly found in news."""
    text = (value or "").strip()
    if not text:
        return None

    iso_text = text.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(iso_text)
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=UTC)
        return parsed.astimezone(UTC)
    except ValueError:
        pass

    normalized = re.sub(r"\s+", " ", text)
    for fmt in (
        "%B %d, %Y, %A", "%B %d, %Y",
        "%b %d, %Y, %A", "%b %d, %Y",
        "%Y-%m-%d",
    ):
        try:
            parsed = datetime.strptime(normalized, fmt)
            return parsed.replace(tzinfo=UTC)
        except ValueError:
            continue

    return None


def average_sentiment(rows: list[dict[str, str]]) -> float:
    if not rows:
        return 0.0
    values = [
        compute_sentiment(f"{row.get('Title', '')} {row.get('Description', '')}")
        for row in rows
    ]
    return sum(values) / len(values)


def _time_decay_weight(row: dict[str, str]) -> float:
    parsed_dt = parse_datetime_text(str(row.get("Date", "") or ""))
    if parsed_dt is None:
        return 0.15

    age_days = max(0.0, (datetime.now(UTC) - parsed_dt).total_seconds() / 86400.0)
    if age_days <= 7:
        return 1.0
    if age_days <= 90:
        return 0.6
    if age_days <= 365:
        base_weight = 0.3
    else:
        base_weight = 0.15

    source_name = str(row.get("Source", "") or "").strip().lower()
    source_weight = SOURCE_QUALITY_WEIGHTS.get(source_name, 1.0)
    return base_weight * source_weight


def weighted_pattern_sentiment(rows: list[dict[str, str]]) -> float:
    if not rows:
        return 0.0

    weighted_sum = 0.0
    total_weight = 0.0

    for row in rows:
        sentiment = compute_sentiment(f"{row.get('Title', '')} {row.get('Description', '')}")
        weight = _time_decay_weight(row)
        weighted_sum += sentiment * weight
        total_weight += weight

    if total_weight <= 0:
        return 0.0
    return weighted_sum / total_weight


def latest_news_date(rows: list[dict[str, str]]) -> str:
    latest_dt: datetime | None = None
    for row in rows:
        parsed_dt = parse_datetime_text(str(row.get("Date", "") or ""))
        if parsed_dt is None:
            continue
        if latest_dt is None or parsed_dt > latest_dt:
            latest_dt = parsed_dt
    if latest_dt is None:
        return ""
    return latest_dt.date().isoformat()


def compute_confidence(recent_count: int, pattern_count: int) -> float:
    recent_component = min(1.0, recent_count / 5.0)
    pattern_component = min(1.0, pattern_count / 40.0)
    score = (0.7 * recent_component) + (0.3 * pattern_component)
    return max(0.0, min(1.0, score))


def extract_drivers(rows: list[dict[str, str]], limit: int = 3) -> tuple[list[str], list[str]]:
    scored: list[tuple[float, str]] = []
    for row in rows:
        title = str(row.get("Title", "") or "").strip()
        description = str(row.get("Description", "") or "").strip()
        if not title:
            continue
        score = compute_sentiment(f"{title} {description}")
        scored.append((score, title))

    positives = [title for score, title in sorted(scored, key=lambda item: item[0], reverse=True) if score > 0]
    negatives = [title for score, title in sorted(scored, key=lambda item: item[0]) if score < 0]
    return positives[:limit], negatives[:limit]


def build_explanation(
    sentiment: float,
    now_sentiment: float,
    pattern_sentiment: float,
    recent_count: int,
    pattern_count: int,
    latest_news_date: str,
    recommendation: str,
    ondemand_fetched: bool = False,
    ticker: str = "",
    fast_news_max_age_days: int = 30,
) -> str:
    if recent_count == 0 and pattern_count == 0:
        return (
            f"No news data found for '{ticker or 'this stock'}'. "
            f"Recommendation defaults to {recommendation} due to insufficient data. "
            f"Try searching for a more common stock symbol or check back later."
        )

    if ondemand_fetched:
        return (
            f"Recommendation {recommendation} is based on {pattern_count} live-fetched headlines "
            f"(no cached data). Sentiment={sentiment:.2f} (now={now_sentiment:.2f}, pattern={pattern_sentiment:.2f})."
        )

    if recent_count == 0 and pattern_count > 0:
        return (
            f"No recent matched headlines in the last {fast_news_max_age_days} days; "
            f"recommendation defaults to {recommendation} and uses historical pattern context. "
            f"Latest matched date: {latest_news_date or 'unknown'}."
        )

    return (
        f"Recommendation {recommendation} is based on combined sentiment={sentiment:.2f} "
        f"(now={now_sentiment:.2f}, pattern={pattern_sentiment:.2f}) using "
        f"{recent_count} recent and {pattern_count} total matched headlines."
    )
