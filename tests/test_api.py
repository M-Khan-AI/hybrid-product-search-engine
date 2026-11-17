def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}


def test_search_ok(client):
    r = client.get("/search", params={"q": "noise cancelling headphones"})
    assert r.status_code == 200
    body = r.json()
    assert body["count"] == len(body["results"]) <= 10
    assert body["cached"] is False
    assert {"id", "title", "price", "score"} <= body["results"][0].keys()


def test_second_call_is_served_from_cache(client):
    client.get("/search", params={"q": "bluetooth speaker"})
    r = client.get("/search", params={"q": "bluetooth speaker"})
    assert r.json()["cached"] is True
    assert client.get("/cache/stats").json()["hits"] == 1


def test_missing_query_is_422(client):
    assert client.get("/search").status_code == 422


def test_empty_query_is_422(client):
    assert client.get("/search", params={"q": ""}).status_code == 422


def test_whitespace_query_is_400(client):
    r = client.get("/search", params={"q": "     "})
    assert r.status_code == 400
    assert "empty" in r.json()["detail"].lower()


def test_punctuation_only_query_is_400(client):
    assert client.get("/search", params={"q": "!!!"}).status_code == 400


def test_too_long_query_is_422(client):
    assert client.get("/search", params={"q": "a" * 201}).status_code == 422


def test_limit_validation(client):
    assert client.get("/search", params={"q": "laptop", "limit": 0}).status_code == 422
    assert client.get("/search", params={"q": "laptop", "limit": 11}).status_code == 422
    r = client.get("/search", params={"q": "laptop", "limit": 4})
    assert r.status_code == 200 and r.json()["count"] == 4


def test_injection_attempt_returns_200_or_400_never_500(client):
    for q in ["' OR 1=1 --", '"; DROP TABLE products;', "laptop AND", "<script>alert(1)</script>"]:
        assert client.get("/search", params={"q": q}).status_code in (200, 400)


def test_clear_cache(client):
    client.get("/search", params={"q": "camera"})
    client.delete("/cache")
    assert client.get("/cache/stats").json()["size"] == 0