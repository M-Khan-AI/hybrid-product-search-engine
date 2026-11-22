"""Input sanitisation: turns raw user text into a safe query and a safe FTS5 MATCH string."""
import re
import unicodedata

from config import MAX_QUERY_LENGTH

MAX_TOKENS = 20
# Very common words that add noise to keyword matching
STOP_WORDS = {
    "a", "an", "the", "for", "to", "of", "and", "or", "in", "with", "on", "at", "by",
    "me", "my", "i", "is", "are", "that", "this", "some", "something", "want", "need",
}
_TOKEN_RE = re.compile(r"\w+", re.UNICODE)


class InvalidQueryError(ValueError):
    """Raised when a query is empty or unusable after cleaning."""


def clean_query(raw) -> str:
    """Normalise unicode, drop control characters, collapse whitespace."""
    if not isinstance(raw, str):
        raise InvalidQueryError("Query must be text.")
    text = unicodedata.normalize("NFKC", raw)
    # remove control/format characters (null bytes, escape codes, zero-width chars ...)
    text = "".join(ch for ch in text if unicodedata.category(ch)[0] != "C" or ch in "\t\n ")
    text = " ".join(text.split())  # collapse tabs/newlines/multiple spaces
    if not text:
        raise InvalidQueryError("Query is empty.")
    if len(text) > MAX_QUERY_LENGTH:
        raise InvalidQueryError(f"Query is too long (max {MAX_QUERY_LENGTH} characters).")
    return text


def extract_tokens(text: str) -> list[str]:
    """Lower-cased word tokens; punctuation, quotes and SQL/FTS symbols are dropped."""
    tokens = _TOKEN_RE.findall(text.lower())
    if not tokens:
        raise InvalidQueryError("Query has no searchable words.")
    useful = [t for t in tokens if t not in STOP_WORDS]
    return (useful or tokens)[:MAX_TOKENS]


def build_fts_query(tokens: list[str]) -> str:
    """Quote every token so FTS5 treats it as plain text (never as OR/NOT/NEAR/* syntax)."""
    return " OR ".join(f'"{t}"' for t in tokens)


def sanitize(raw) -> tuple[str, list[str]]:
    """Returns (cleaned_text, tokens). Raises InvalidQueryError for unusable input."""
    text = clean_query(raw)
    return text, extract_tokens(text)