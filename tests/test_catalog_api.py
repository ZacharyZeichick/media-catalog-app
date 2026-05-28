def test_list_returns_200(client):
    r = client.get("/api/media")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_limit(client):
    r = client.get("/api/media?limit=5")
    assert r.status_code == 200
    assert len(r.json()) <= 5


def test_search_by_title(client):
    r = client.get("/api/media?q=the")
    assert r.status_code == 200
    data = r.json()
    assert len(data) > 0
    assert all("the" in item["title"].lower() for item in data)


def test_min_rating(client):
    r = client.get("/api/media?min_rating=9.0")
    assert r.status_code == 200
    data = r.json()
    assert len(data) > 0
    assert all(item["rating"] >= 9.0 for item in data)


def test_year_filter(client):
    r = client.get("/api/media?year=2022")
    assert r.status_code == 200
    data = r.json()
    assert len(data) > 0
    assert all(item["year"] == 2022 for item in data)


def test_sort_by_rating_desc(client):
    r = client.get("/api/media?sort_by=rating&sort_dir=desc")
    assert r.status_code == 200
    data = r.json()
    ratings = [item["rating"] for item in data if item["rating"] is not None]
    assert ratings == sorted(ratings, reverse=True)


def test_invalid_sort_by_returns_422(client):
    r = client.get("/api/media?sort_by=invalid")
    assert r.status_code == 422
