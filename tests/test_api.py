import json

import pytest

from app.services.gemini import GeminiError


def _patch_gemini(monkeypatch, result=None, raise_on_call=None):
    class Client:
        def review(self, *args, **kwargs):
            if raise_on_call:
                raise raise_on_call
            return {
                "updated_risk_score": 0.0,
                "unusual_pattern_detected": False,
                **(result or {}),
            }

    monkeypatch.setattr("app.services.scoring.get_gemini_client", lambda: Client())


class TestHealthEndpoint:
    def test_health_returns_ok(self, client):
        response = client.get("/api/health")
        assert response.status_code == 200
        data = response.get_json()
        assert data["status"] == "ok"
        assert "environment" in data


class TestHomePage:
    def test_homepage_includes_startup_fallback(self, client):
        response = client.get("/")
        assert response.status_code == 200
        assert b'id="startup-view"' in response.data
        assert b'id="startup-retry"' in response.data
        assert b'<script defer src="https://cdn.jsdelivr.net/npm/@supabase' in response.data


class TestSingleScreenEndpoint:
    def test_screen_low_risk(self, client, monkeypatch):
        _patch_gemini(monkeypatch, result={"updated_risk_score": 0.0})
        payload = {
            "transactionId": "TX-API-1",
            "amount": 100.0,
            "currency": "USD",
            "senderName": "Alice",
            "senderCountry": "US",
            "receiverName": "Bob",
            "receiverCountry": "US",
        }
        response = client.post("/api/screen/single", json=payload)
        assert response.status_code == 200
        data = response.get_json()
        assert data["transaction_id"] == "TX-API-1"
        assert data["final_score"] == 0.0
        assert data["classification"] == "No Match / Low Risk"

    def test_screen_high_risk(self, client, monkeypatch):
        _patch_gemini(
            monkeypatch,
            result={
                "updated_risk_score": 1.0,
                "unusual_pattern_detected": True,
            },
        )
        payload = {
            "transactionId": "TX-API-2",
            "amount": 5000.0,
            "currency": "USD",
            "senderName": "Alice",
            "senderCountry": "US",
            "receiverName": "Kim Jong Un",
            "receiverCountry": "KP",
        }
        response = client.post("/api/screen/single", json=payload)
        assert response.status_code == 200
        data = response.get_json()
        assert data["final_score"] == 1.0
        assert data["classification"] == "Definite Match / High Risk"
        assert data["gemini_reviewed"] is True

    def test_gemini_failure_returns_503(self, client, monkeypatch):
        _patch_gemini(monkeypatch, raise_on_call=GeminiError("model unavailable"))
        payload = {
            "transactionId": "TX-API-3",
            "amount": 5000.0,
            "currency": "USD",
            "senderName": "Alice",
            "senderCountry": "US",
            "receiverName": "Bob",
            "receiverCountry": "US",
        }
        response = client.post("/api/screen/single", json=payload)
        assert response.status_code == 503
        data = response.get_json()
        assert data["error"] == "Gemini review failed"


class TestBatchScreenEndpoint:
    def test_batch_accepts_json_list(self, client, monkeypatch):
        _patch_gemini(monkeypatch, result={"updated_risk_score": 0.0})
        transactions = [
            {
                "transactionId": "TX-B-1",
                "transactionDate": "2026-10-19",
                "transactionType": "wire",
                "amount": 50.0,
                "currency": "USD",
                "senderName": "A",
                "senderCountry": "US",
                "receiverName": "B",
                "receiverCountry": "US",
            },
            {
                "transactionId": "TX-B-2",
                "transactionDate": "2026-10-19",
                "transactionType": "wire",
                "amount": 2000.0,
                "currency": "USD",
                "senderName": "C",
                "senderCountry": "US",
                "receiverName": "D",
                "receiverCountry": "US",
            },
        ]
        response = client.post("/api/screen/batch", json=transactions)
        assert response.status_code == 200
        data = response.get_json()
        assert data["count"] == 2
        assert data["results"][0]["classification"] == "No Match / Low Risk"
        assert data["results"][1]["gemini_reviewed"] is True

    def test_batch_rejects_non_list_body(self, client):
        response = client.post("/api/screen/batch", json={"not": "a list"})
        assert response.status_code == 400


class TestAuthEndpoint:
    def test_me_when_auth_disabled(self, client):
        response = client.get("/api/auth/me")
        assert response.status_code == 200
        data = response.get_json()
        assert data["authenticated"] is False


class TestScreeningsEndpoint:
    def test_list_screenings_requires_no_auth_in_tests(self, client):
        response = client.get("/api/screenings")
        assert response.status_code == 200
        data = response.get_json()
        assert "screenings" in data


class TestCasesEndpoint:
    def test_create_case_missing_screening_id(self, client):
        response = client.post("/api/cases", json={})
        assert response.status_code == 400

    def test_cases_list_requires_no_auth_in_tests(self, client):
        response = client.get("/api/cases")
        assert response.status_code == 200
        data = response.get_json()
        assert "cases" in data


class TestAsyncBatchEndpoint:
    def test_async_batch_without_supabase_returns_503(self, client, monkeypatch):
        _patch_gemini(monkeypatch, result={"updated_risk_score": 0.0})
        transactions = [
            {
                "transactionId": "TX-ASYNC-1",
                "transactionDate": "2026-10-19",
                "transactionType": "wire",
                "amount": 50.0,
                "currency": "USD",
                "senderName": "A",
                "senderCountry": "US",
                "receiverName": "B",
                "receiverCountry": "US",
            }
        ]
        response = client.post("/api/screen/batch?async=true", json=transactions)
        assert response.status_code == 503
