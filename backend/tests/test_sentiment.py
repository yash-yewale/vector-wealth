"""Tests for the sentiment scoring engine."""
import pytest
from sentiment import (
    compute_sentiment,
    compute_confidence,
    extract_drivers,
    build_explanation,
    average_sentiment,
    latest_news_date,
    parse_datetime_text,
)


class TestComputeSentiment:
    """Test the core sentiment scoring function."""

    def test_strong_positive(self):
        score = compute_sentiment("Stock surges 20% on record profits")
        assert score > 0.3, f"Expected strong positive, got {score}"

    def test_strong_negative(self):
        score = compute_sentiment("Share price plunges amid massive losses")
        assert score < -0.3, f"Expected strong negative, got {score}"

    def test_neutral_text(self):
        score = compute_sentiment("Company announces quarterly results")
        assert -0.3 < score < 0.3, f"Expected neutral, got {score}"

    def test_empty_string(self):
        assert compute_sentiment("") == 0.0

    def test_none_string(self):
        assert compute_sentiment(None) == 0.0

    def test_negation_reversal(self):
        """'no gains' should be negative, not positive."""
        positive = compute_sentiment("company reports gains")
        negated = compute_sentiment("company reports no gains")
        assert negated < positive, f"Negation should reduce score: {negated} vs {positive}"

    def test_intensifier_scaling(self):
        """'massive surge' > 'slight rise' before clamping effects."""
        massive = compute_sentiment("Stocks show massive surge but also some decline")
        slight = compute_sentiment("Stocks show slight rise but also some decline")
        assert massive > slight, f"Intensifier should scale: massive={massive}, slight={slight}"

    def test_contrast_handling(self):
        """Text with 'but' should shift sentiment toward the latter clause."""
        pure_negative = compute_sentiment("Stock falls and faces losses")
        contrasted = compute_sentiment("Stock falls but gains strong profit")
        assert contrasted > pure_negative, f"Contrast should improve score: {contrasted} vs {pure_negative}"

    def test_range_clamping(self):
        """Score should always be in [-1, 1]."""
        score = compute_sentiment("surge surge surge surge gains gains gains record profits")
        assert -1.0 <= score <= 1.0


class TestComputeConfidence:
    def test_full_confidence(self):
        conf = compute_confidence(recent_count=5, pattern_count=40)
        assert conf == 1.0

    def test_zero_data(self):
        conf = compute_confidence(recent_count=0, pattern_count=0)
        assert conf == 0.0

    def test_partial_data(self):
        conf = compute_confidence(recent_count=2, pattern_count=10)
        assert 0.0 < conf < 1.0


class TestExtractDrivers:
    def test_separates_positive_negative(self):
        rows = [
            {"Title": "Stock surges on strong results", "Description": ""},
            {"Title": "Company faces massive losses", "Description": ""},
            {"Title": "Revenue growth beats expectations", "Description": ""},
        ]
        pos, neg = extract_drivers(rows)
        assert len(pos) > 0
        assert len(neg) > 0

    def test_empty_rows(self):
        pos, neg = extract_drivers([])
        assert pos == []
        assert neg == []


class TestBuildExplanation:
    def test_no_data(self):
        result = build_explanation(
            sentiment=0.0, now_sentiment=0.0, pattern_sentiment=0.0,
            recent_count=0, pattern_count=0, latest_news_date="",
            recommendation="HOLD", ticker="XYZ",
        )
        assert "No news data found" in result

    def test_ondemand_fetched(self):
        result = build_explanation(
            sentiment=0.5, now_sentiment=0.5, pattern_sentiment=0.5,
            recent_count=5, pattern_count=5, latest_news_date="2026-01-01",
            recommendation="BUY", ondemand_fetched=True,
        )
        assert "live-fetched" in result

    def test_normal_analysis(self):
        result = build_explanation(
            sentiment=0.3, now_sentiment=0.4, pattern_sentiment=0.2,
            recent_count=3, pattern_count=8, latest_news_date="2026-01-15",
            recommendation="BUY",
        )
        assert "BUY" in result
        assert "0.30" in result


class TestParseDatetimeText:
    def test_iso_format(self):
        dt = parse_datetime_text("2026-01-15T10:30:00Z")
        assert dt is not None
        assert dt.year == 2026

    def test_date_only(self):
        dt = parse_datetime_text("2026-01-15")
        assert dt is not None

    def test_empty(self):
        assert parse_datetime_text("") is None

    def test_verbose_format(self):
        dt = parse_datetime_text("January 15, 2026, Wednesday")
        assert dt is not None


class TestLatestNewsDate:
    def test_returns_latest(self):
        rows = [
            {"Date": "2026-01-10"},
            {"Date": "2026-01-20"},
            {"Date": "2026-01-05"},
        ]
        assert latest_news_date(rows) == "2026-01-20"

    def test_empty_rows(self):
        assert latest_news_date([]) == ""


class TestAverageSentiment:
    def test_mixed_headlines(self):
        rows = [
            {"Title": "Stock surges", "Description": "strong gains"},
            {"Title": "Stock plunges", "Description": "massive losses"},
        ]
        avg = average_sentiment(rows)
        assert -0.5 < avg < 0.5, f"Mixed should be near-neutral: {avg}"

    def test_empty(self):
        assert average_sentiment([]) == 0.0
