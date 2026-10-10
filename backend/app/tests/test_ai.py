from typing import Any, Optional

import pytest

import app.services.geocoding_service as geocoding_module
from app.main import app
from app.routers import ai as ai_router
from app.tests.helpers import (
    auth_headers,
    create_lawyer_profile,
    register_lawyer,
    register_user,
)


class FakeAI:
    def __init__(self) -> None:
        self.configured = True

    async def chat(self, message: str, history: Optional[list] = None) -> str:
        return "This is a helpful, concise legal answer."

    async def summarize(self, text: str) -> str:
        return "Summary of the legal document."

    async def answer_faq(self, question: str) -> dict[str, Any]:
        return {
            "answer": "You generally have a right to a lawyer in criminal matters.",
            "related_categories": ["criminal"],
            "suggested_action": "Consult a criminal lawyer.",
        }

    async def predict_category(
        self, description: str, categories: list[str]
    ) -> dict[str, Any]:
        return {
            "category": "family" if "family" in categories else categories[0],
            "confidence": 0.9,
            "explanation": "The issue relates to family matters.",
        }

    async def translate(self, text: str, target_language: str) -> str:
        return "Texto traducido al espanol."


class UnconfiguredAI(FakeAI):
    def __init__(self) -> None:
        super().__init__()
        self.configured = False

    async def chat(self, message: str, history: Optional[list] = None) -> str:
        from app.services.ai_service import AIError

        raise AIError("AI is not configured. Set OPENAI_API_KEY in your .env file.")


class RateLimitedAI(FakeAI):
    async def chat(self, message: str, history: Optional[list] = None) -> str:
        from app.services.ai_service import AIError

        raise AIError(
            "The AI provider is rate-limiting requests or the API key's quota is exhausted "
            "(HTTP 429). Try again later or check your API key's quota."
        )


def _override(fake):
    def _dep():
        return fake

    return _dep


@pytest.fixture
async def ai_client(client):
    fake = FakeAI()
    user = await register_user(client, email="ai_user@example.com")
    client.headers.update(auth_headers(user))
    app.dependency_overrides[ai_router._get_ai] = _override(fake)
    yield client
    app.dependency_overrides.pop(ai_router._get_ai, None)


async def test_ai_requires_authentication(client):
    resp = await client.post("/api/v1/ai/chat", json={"message": "hello"})
    assert resp.status_code == 401


async def test_ai_not_configured_returns_503(ai_client):
    fake = UnconfiguredAI()
    app.dependency_overrides[ai_router._get_ai] = _override(fake)
    try:
        resp = await ai_client.post("/api/v1/ai/chat", json={"message": "hello"})
        assert resp.status_code == 503
        assert "OPENAI_API_KEY" in resp.json()["detail"]
    finally:
        app.dependency_overrides.pop(ai_router._get_ai, None)


async def test_ai_provider_rate_limit_surfaces_clear_message(ai_client):
    fake = RateLimitedAI()
    app.dependency_overrides[ai_router._get_ai] = _override(fake)
    try:
        resp = await ai_client.post("/api/v1/ai/chat", json={"message": "hello"})
        assert resp.status_code == 503
        assert "429" in resp.json()["detail"]
        assert "quota" in resp.json()["detail"]
    finally:
        app.dependency_overrides.pop(ai_router._get_ai, None)


async def test_ai_chat(ai_client):
    resp = await ai_client.post("/api/v1/ai/chat", json={"message": "What is a contract?"})
    assert resp.status_code == 200
    data = resp.json()
    assert "reply" in data
    assert data["reply"]


async def test_ai_chat_validates_empty_message(ai_client):
    resp = await ai_client.post("/api/v1/ai/chat", json={"message": ""})
    assert resp.status_code == 422


async def test_ai_summarize(ai_client):
    resp = await ai_client.post(
        "/api/v1/ai/summarize", json={"text": "This agreement is a long legal document."}
    )
    assert resp.status_code == 200
    assert resp.json()["summary"]


async def test_ai_faq(ai_client):
    resp = await ai_client.post(
        "/api/v1/ai/faq", json={"question": "Do I need a lawyer?"}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["answer"]
    assert "criminal" in data["related_categories"]
    assert data["suggested_action"]


async def test_ai_predict_category(ai_client):
    resp = await ai_client.post(
        "/api/v1/ai/predict-category",
        json={"description": "I want a divorce and child custody."},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["category"] == "family"
    assert 0.0 <= data["confidence"] <= 1.0
    assert data["explanation"]


async def test_ai_translate(ai_client):
    resp = await ai_client.post(
        "/api/v1/ai/translate",
        json={"text": "Please contact your lawyer.", "target_language": "Spanish"},
    )
    assert resp.status_code == 200
    assert resp.json()["translated"]


async def test_ai_recommend_lawyers(client):
    fake = FakeAI()
    app.dependency_overrides[ai_router._get_ai] = _override(fake)
    try:
        lawyer = await register_lawyer(client, email="rec_lawyer@example.com")
        profile = await create_lawyer_profile(client, lawyer)
        resp = await client.post(
            "/api/v1/ai/recommend-lawyers",
            headers=auth_headers(lawyer),
            json={"description": "Help with my divorce case."},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "recommendations" in data
        assert len(data["recommendations"]) == 1
        assert data["recommendations"][0]["user_id"] == lawyer["user"]["id"]
    finally:
        app.dependency_overrides.pop(ai_router._get_ai, None)


async def test_ai_nearby_lawyers(client):
    lawyer = await register_lawyer(client, email="geo_lawyer@example.com")
    resp = await client.put(
        "/api/v1/lawyers/me/profile",
        headers=auth_headers(lawyer),
        json={
            "bio": "Family lawyer",
            "years_of_experience": 5,
            "categories": ["family"],
            "city": "Mumbai",
            "latitude": 19.076,
            "longitude": 72.8777,
        },
    )
    assert resp.status_code == 200, resp.text
    resp2 = await client.get(
        "/api/v1/ai/nearby-lawyers",
        params={"lat": 19.076, "lng": 72.8777, "radius_km": 50},
        headers=auth_headers(lawyer),
    )
    assert resp2.status_code == 200
    data = resp2.json()
    assert data["total"] == 1
    assert data["items"][0]["distance_km"] == 0.0

    # A lawyer without coordinates should not appear on the map.
    lawyer2 = await register_lawyer(client, email="nogeo_lawyer@example.com")
    await client.put(
        "/api/v1/lawyers/me/profile",
        headers=auth_headers(lawyer2),
        json={"bio": "No geo", "years_of_experience": 2, "categories": ["civil"]},
    )
    resp3 = await client.get(
        "/api/v1/ai/nearby-lawyers",
        params={"lat": 19.076, "lng": 72.8777},
        headers=auth_headers(lawyer),
    )
    assert resp3.json()["total"] == 1


async def test_ai_nearby_lawyers_distance_sort_and_filter(client):
    near = await register_lawyer(client, email="near_sort@example.com")
    await client.put(
        "/api/v1/lawyers/me/profile",
        headers=auth_headers(near),
        json={
            "bio": "Nearby",
            "years_of_experience": 1,
            "categories": ["family"],
            "latitude": 19.076,
            "longitude": 72.8777,
        },
    )
    far = await register_lawyer(client, email="far_sort@example.com")
    await client.put(
        "/api/v1/lawyers/me/profile",
        headers=auth_headers(far),
        json={
            "bio": "Far away",
            "years_of_experience": 1,
            "categories": ["family"],
            "latitude": 28.6139,
            "longitude": 77.2090,
        },
    )

    resp = await client.get(
        "/api/v1/ai/nearby-lawyers",
        params={"lat": 19.076, "lng": 72.8777, "sort": "distance"},
        headers=auth_headers(near),
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["total"] == 2
    assert data["items"][0]["user_id"] == near["user"]["id"]
    assert data["items"][0]["distance_km"] == 0.0
    assert data["items"][1]["distance_km"] > data["items"][0]["distance_km"]

    # A radius filter keeps only lawyers inside the requested distance.
    filtered = await client.get(
        "/api/v1/ai/nearby-lawyers",
        params={"lat": 19.076, "lng": 72.8777, "radius_km": 10},
        headers=auth_headers(near),
    )
    assert filtered.status_code == 200
    assert filtered.json()["total"] == 1
    assert filtered.json()["items"][0]["user_id"] == near["user"]["id"]


class FakeGeocoder:
    """Deterministic geocoder so the resolution tests never touch the network."""

    def __init__(self, results: dict[str, Optional[tuple[float, float]]]) -> None:
        self.results = results

    async def geocode_city(self, city: str) -> Optional[tuple[float, float]]:
        key = " ".join((city or "").strip().lower().split())
        return self.results.get(key)


async def test_ai_nearby_lawyers_geocodes_city_only_lawyer(client, monkeypatch):
    """A lawyer with only a city name (e.g. the seeded Pankaj Tripathi/Nagpur
    case) gets real, persisted coordinates and sorts nearest-first."""
    monkeypatch.setattr(
        geocoding_module,
        "geocoding_service",
        FakeGeocoder({"nagpur": (21.1458, 79.0882)}),
    )

    nagpur = await register_lawyer(
        client, name="Pankaj Tripathi", email="pankaj_tripathi@example.com"
    )
    resp = await client.put(
        "/api/v1/lawyers/me/profile",
        headers=auth_headers(nagpur),
        json={
            "bio": "Civil lawyer based in Nagpur",
            "years_of_experience": 10,
            "categories": ["civil"],
            "city": "Nagpur",
        },
    )
    assert resp.status_code == 200

    far = await register_lawyer(
        client, name="Delhi Lawyer", email="delhi_far@example.com"
    )
    await client.put(
        "/api/v1/lawyers/me/profile",
        headers=auth_headers(far),
        json={
            "bio": "Corporate lawyer",
            "years_of_experience": 8,
            "categories": ["corporate"],
            "city": "New Delhi",
            "latitude": 28.6139,
            "longitude": 77.2090,
        },
    )

    resp = await client.get(
        "/api/v1/ai/nearby-lawyers",
        params={"lat": 21.1458, "lng": 79.0882, "sort": "distance"},
        headers=auth_headers(nagpur),
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["total"] == 2
    items = data["items"]
    assert items[0]["user_id"] == nagpur["user"]["id"]
    assert items[0]["distance_km"] is not None
    assert items[0]["distance_km"] <= 1.0
    assert items[1]["user_id"] == far["user"]["id"]
    assert items[1]["distance_km"] > items[0]["distance_km"]

    # The resolved coordinates were persisted to the lawyer's profile.
    profile = await client.get(
        "/api/v1/lawyers/me/profile", headers=auth_headers(nagpur)
    )
    assert profile.status_code == 200
    assert profile.json()["latitude"] == pytest.approx(21.1458)
    assert profile.json()["longitude"] == pytest.approx(79.0882)

    # Re-running the search (a refresh) keeps the identical nearest-first order.
    resp2 = await client.get(
        "/api/v1/ai/nearby-lawyers",
        params={"lat": 21.1458, "lng": 79.0882, "sort": "distance"},
        headers=auth_headers(nagpur),
    )
    assert resp2.status_code == 200
    assert [i["user_id"] for i in resp2.json()["items"]] == [
        i["user_id"] for i in items
    ]


async def test_ai_nearby_lawyers_excludes_city_that_cannot_geocode(client, monkeypatch):
    """A lawyer whose city cannot be resolved is excluded gracefully."""
    monkeypatch.setattr(
        geocoding_module,
        "geocoding_service",
        FakeGeocoder({"unknownville": None}),
    )
    lawyer = await register_lawyer(client, email="unknownville@example.com")
    await client.put(
        "/api/v1/lawyers/me/profile",
        headers=auth_headers(lawyer),
        json={
            "bio": "Practises somewhere unknown",
            "years_of_experience": 3,
            "categories": ["family"],
            "city": "Unknownville",
        },
    )
    resp = await client.get(
        "/api/v1/ai/nearby-lawyers",
        params={"lat": 21.1458, "lng": 79.0882, "sort": "distance"},
        headers=auth_headers(lawyer),
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["total"] == 0
