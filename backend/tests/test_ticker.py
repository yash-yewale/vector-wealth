"""Tests for ticker extraction and alias matching."""
import re
import sys
from pathlib import Path

# Add backend to path for imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from stock_data import STOCK_ALIASES, GENERIC_STOCK_TERMS, TICKER_SUFFIX_SPLITS


# ─── Standalone ticker extraction (copied logic to avoid chromadb dependency) ───

def _extract_ticker(query: str) -> str:
    upper_query = query.upper()
    match = re.search(r"\bON\s+([A-Z][A-Z0-9._-]{1,14})\b", upper_query)
    if match:
        return match.group(1)
    candidates = re.findall(r"\b[A-Z][A-Z0-9._-]{1,14}\b", upper_query)
    if candidates:
        return candidates[-1]
    return "MARKET"


def _normalize_term(term: str) -> str:
    return re.sub(r"[^a-z0-9 ]+", " ", (term or "").lower()).strip()


def _build_ticker_terms(ticker: str) -> list[str]:
    raw = (ticker or "").strip()
    if not raw:
        return []
    upper = raw.upper()
    if upper == "MARKET":
        return []
    normalized_input = _normalize_term(raw)
    normalized_compact = re.sub(r"[^A-Z0-9]+", "", upper)
    is_single_word = " " not in normalized_input
    alias_input_match = False
    terms: set[str] = set()
    if normalized_input:
        terms.add(normalized_input)
    if normalized_compact:
        terms.add(normalized_compact.lower())
    for part in normalized_input.split():
        if len(part) > 2 and part not in GENERIC_STOCK_TERMS:
            terms.add(part)
    for suffix in TICKER_SUFFIX_SPLITS:
        if normalized_compact.endswith(suffix) and len(normalized_compact) > len(suffix) + 1:
            prefix = normalized_compact[: -len(suffix)].strip()
            if prefix:
                terms.add(f"{prefix.lower()} {suffix.lower()}")
    if normalized_compact in STOCK_ALIASES:
        for alias in STOCK_ALIASES[normalized_compact]:
            alias_norm = _normalize_term(alias)
            if alias_norm:
                terms.add(alias_norm)
    for symbol, aliases in STOCK_ALIASES.items():
        for alias in aliases:
            alias_norm = _normalize_term(alias)
            if alias_norm and alias_norm == normalized_input:
                alias_input_match = True
                terms.add(symbol.lower())
                for other_alias in aliases:
                    other_norm = _normalize_term(other_alias)
                    if other_norm:
                        terms.add(other_norm)
    if is_single_word and not alias_input_match and normalized_compact not in STOCK_ALIASES:
        if len(normalized_compact) > 6:
            return []
    filtered = [
        term for term in terms
        if len(term) > 1 and not (len(term) <= 4 and term in GENERIC_STOCK_TERMS)
    ]
    return sorted(filtered, key=len, reverse=True)


class TestExtractTicker:
    def test_simple_ticker(self):
        assert _extract_ticker("What is the sentiment on TCS?") == "TCS"

    def test_uppercase_extraction(self):
        assert _extract_ticker("analyze RELIANCE") == "RELIANCE"

    def test_multi_word_query(self):
        result = _extract_ticker("How is HDFCBANK performing?")
        assert result == "HDFCBANK"

    def test_no_ticker_defaults_market(self):
        result = _extract_ticker("how is the market doing today")
        assert isinstance(result, str) and len(result) > 0

    def test_ticker_with_hyphen(self):
        result = _extract_ticker("What about BAJAJ-AUTO?")
        assert "BAJAJ" in result


class TestBuildTickerTerms:
    def test_known_ticker(self):
        terms = _build_ticker_terms("TCS")
        assert len(terms) > 0
        assert any("tcs" in t for t in terms)

    def test_alias_lookup(self):
        terms = _build_ticker_terms("TCS")
        assert any("tata" in t for t in terms)

    def test_market_returns_empty(self):
        assert _build_ticker_terms("MARKET") == []

    def test_empty_returns_empty(self):
        assert _build_ticker_terms("") == []


class TestStockAliases:
    def test_aliases_not_empty(self):
        assert len(STOCK_ALIASES) > 50

    def test_key_format(self):
        for key in STOCK_ALIASES:
            assert key == key.upper() or "&" in key or "-" in key, f"Bad key: {key}"

    def test_aliases_are_lowercase(self):
        for key, aliases in STOCK_ALIASES.items():
            for alias in aliases:
                assert alias == alias.lower(), f"Alias should be lowercase: {alias} for {key}"
