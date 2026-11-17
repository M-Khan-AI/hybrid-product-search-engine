import pytest

from app.sanitize import InvalidQueryError, build_fts_query, clean_query, sanitize


def test_normal_query_is_tokenised():
    text, tokens = sanitize("Wireless Headphones")
    assert text == "Wireless Headphones"
    assert tokens == ["wireless", "headphones"]


def test_whitespace_is_collapsed():
    assert clean_query("  gaming \t  monitor \n ") == "gaming monitor"


@pytest.mark.parametrize("bad", ["", "   ", "\n\t", "\x00\x01", None, 123])
def test_empty_or_non_text_is_rejected(bad):
    with pytest.raises(InvalidQueryError):
        sanitize(bad)


@pytest.mark.parametrize("bad", ["!!!", "???***", '"" ""', "-- ;"])
def test_punctuation_only_is_rejected(bad):
    with pytest.raises(InvalidQueryError):
        sanitize(bad)


def test_too_long_query_is_rejected():
    with pytest.raises(InvalidQueryError):
        sanitize("a" * 500)


def test_control_characters_are_removed():
    assert clean_query("lap\x00top\x1b") == "laptop"


def test_stop_words_removed_but_kept_if_nothing_else():
    assert sanitize("a laptop for the students")[1] == ["laptop", "students"]
    assert sanitize("the and for")[1] == ["the", "and", "for"]


def test_fts_operators_are_neutralised():
    _, tokens = sanitize('laptop" OR 1=1 --')
    match = build_fts_query(tokens)
    # every token is wrapped in quotes so FTS5 treats it as plain text
    assert all(part.startswith('"') and part.endswith('"') for part in match.split(" OR "))
    assert "--" not in match and "=" not in match


def test_token_count_is_limited():
    _, tokens = sanitize(" ".join(f"w{i}" for i in range(40)))
    assert len(tokens) == 20