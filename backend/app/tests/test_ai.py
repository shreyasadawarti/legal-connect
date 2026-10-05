from typing import Any, Optional

import pytest

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
    app.dependency_overrides[ai_router._get_ai] = _override(fake)
    yield client
    app.dependency_overrides.pop(ai_router._get_ai, None)


async def test_ai_not_configured_returns_503(client):
    fake = UnconfiguredAI()
    app.dependency_overrides[ai_router._get_ai] = _override(fake)
    try:
        resp = await client.post("/api/v1/ai/chat", json={"message": "hello"})
        assert resp.status_code == 503
        assert "OPENAI_API_KEY" in resp.json()["detail"]
    finally:
        app.dependency_overrides.pop(ai_router._get_ai, None)


async def test_ai_provider_rate_limit_surfaces_clear_message(client):
    fake = RateLimitedAI()
    app.dependency_overrides[ai_router._get_ai] = _override(fake)
    try:
        resp = await client.post("/api/v1/ai/chat", json={"message": "hello"})
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
        "/api/v1/ai/nearby-lawyers", params={"lat": 19.076, "lng": 72.8777, "radius_km": 50}
    )
    assert resp2.status_code == 200
    data = resp2.json()
    assert data["total"] == 1

    # A lawyer without coordinates should not appear on the map.
    lawyer2 = await register_lawyer(client, email="nogeo_lawyer@example.com")
    await client.put(
        "/api/v1/lawyers/me/profile",
        headers=auth_headers(lawyer2),
        json={"bio": "No geo", "years_of_experience": 2, "categories": ["civil"]},
    )
    resp3 = await client.get(
        "/api/v1/ai/nearby-lawyers", params={"lat": 19.076, "lng": 72.8777}
    )
    assert resp3.json()["total"] == 1
