from app.sanitize import InvalidQueryError
import pytest


def test_returns_at_most_10_sorted_results(engine):
    res = engine.search("wireless headphones")
    assert 0 < res["count"] <= 10
    scores = [r["score"] for r in res["results"]]
    assert scores == sorted(scores, reverse=True)
    assert all(0.0 <= s <= 1.0 for s in scores)


def test_relevant_category_ranks_first(engine):
    res = engine.search("gaming monitor")
    assert res["results"][0]["category"] == "Monitors"


def test_result_has_both_score_components(engine):
    top = engine.search("laptop for students")["results"][0]
    assert {"bm25_score", "vector_score", "score"} <= top.keys()


def test_limit_is_respected(engine):
    assert engine.search("laptop", limit=3)["count"] == 3


def test_limit_is_clamped_to_10(engine):
    assert engine.search("laptop", limit=999)["count"] <= 10


def test_no_keyword_match_falls_back_to_semantic(engine):
    res = engine.search("zzzqqq nonexistentword")
    assert res["count"] >= 0           # must not crash
    assert isinstance(res["results"], list)


def test_sql_injection_text_is_harmless(engine):
    res = engine.search("'; DROP TABLE products; --")
    assert isinstance(res["results"], list)
    assert engine.search("laptop")["count"] > 0   # table still exists


def test_fts_syntax_does_not_break_search(engine):
    for q in ['laptop AND', 'NOT phone', '"unclosed', 'NEAR(a b)', 'col:value*', '(((']:
        try:
            engine.search(q)
        except InvalidQueryError:
            pass     # rejecting is fine; crashing with sqlite3.OperationalError is not


def test_unicode_query_does_not_crash(engine):
    engine.search("سمارٹ فون")
    engine.search("手机 laptop")


def test_empty_query_raises(engine):
    with pytest.raises(InvalidQueryError):
        engine.search("   ")


# ---- cache behaviour ----
def test_second_identical_query_is_cached(engine):
    assert engine.search("smart watch")["cached"] is False
    assert engine.search("smart watch")["cached"] is True
    assert engine.cache.stats()["hits"] == 1


def test_equivalent_queries_share_cache_entry(engine):
    engine.search("Gaming   MONITOR")
    assert engine.search("gaming monitor!")["cached"] is True


def test_different_limit_is_a_different_cache_entry(engine):
    engine.search("laptop", limit=5)
    assert engine.search("laptop", limit=3)["cached"] is False


def test_lru_evicts_oldest_entry(engine):          # cache size is 3 in the fixture
    for q in ["laptop", "phone", "camera"]:
        engine.search(q)
    engine.search("laptop")                         # laptop becomes most recently used
    engine.search("speaker")                        # evicts "phone" (least recently used)
    assert engine.search("laptop")["cached"] is True
    assert engine.search("phone")["cached"] is False


def test_cached_result_matches_fresh_result(engine):
    first = engine.search("tablet")
    second = engine.search("tablet")
    assert first["results"] == second["results"]