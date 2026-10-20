import json

import pytest

from app.services.gemini import (
    GeminiClient,
    GeminiError,
    _parse_gemini_response,
    get_gemini_client,
)


class TestParseGeminiResponse:
    def test_valid_response(self):
        text = json.dumps(
            {
                "updated_risk_score": 0.75,
                "unusual_pattern_detected": True,
                "confidence": 0.9,
                "reasoning": "Sanctions hit with weak context.",
                "false_positive_assessment": "Possible false positive.",
            }
        )
        payload = {"candidates": [{"content": {"parts": [{"text": text}]}}]}
        result = _parse_gemini_response(payload)

        assert result["updated_risk_score"] == 0.75
        assert result["unusual_pattern_detected"] is True
        assert result["confidence"] == 0.9
        assert result["reasoning"] == "Sanctions hit with weak context."
        assert result["false_positive_assessment"] == "Possible false positive."

    @pytest.mark.parametrize(
        "payload",
        [
            {},
            {"candidates": []},
            {"candidates": [{"content": {"parts": []}}]},
            {"candidates": [{"content": {"parts": [{"text": "not json"}]}}]},
        ],
    )
    def test_malformed_payload_raises(self, payload):
        with pytest.raises(GeminiError):
            _parse_gemini_response(payload)

    def test_non_boolean_unusual_pattern_raises(self):
        text = json.dumps(
            {
                "updated_risk_score": 0.2,
                "unusual_pattern_detected": "false",
                "confidence": 0.5,
                "reasoning": "No unusual pattern.",
                "false_positive_assessment": "Not applicable.",
            }
        )
        payload = {"candidates": [{"content": {"parts": [{"text": text}]}}]}
        with pytest.raises(GeminiError, match="non-boolean"):
            _parse_gemini_response(payload)

    def test_missing_keys_raises(self):
        text = json.dumps({"updated_risk_score": 0.5, "confidence": 0.5})
        payload = {"candidates": [{"content": {"parts": [{"text": text}]}}]}
        with pytest.raises(GeminiError):
            _parse_gemini_response(payload)

    @pytest.mark.parametrize("score", [-0.1, 1.1])
    def test_out_of_range_score_raises(self, score):
        text = json.dumps(
            {
                "updated_risk_score": score,
                "unusual_pattern_detected": False,
                "confidence": 0.5,
                "reasoning": "x",
                "false_positive_assessment": "y",
            }
        )
        payload = {"candidates": [{"content": {"parts": [{"text": text}]}}]}
        with pytest.raises(GeminiError):
            _parse_gemini_response(payload)


class TestGeminiClient:
    def test_missing_api_key_raises(self, monkeypatch):
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        with pytest.raises(GeminiError):
            get_gemini_client()

    def test_review_returns_parsed_result(self, monkeypatch):
        fake_response = {
            "candidates": [
                {
                    "content": {
                        "parts": [
                            {
                                "text": json.dumps(
                                    {
                                        "updated_risk_score": 0.65,
                                        "unusual_pattern_detected": False,
                                        "confidence": 0.8,
                                        "reasoning": "Medium risk.",
                                        "false_positive_assessment": "Unlikely.",
                                    }
                                )
                            }
                        ]
                    }
                }
            ]
        }

        class FakeResponse:
            def json(self):
                return fake_response

            def raise_for_status(self):
                pass

        class FakeSession:
            def post(self, url, json, timeout):
                assert "gemini" in url
                return FakeResponse()

        client = GeminiClient("dummy-key")
        monkeypatch.setattr(client, "session", FakeSession())

        result = client.review({}, 0.5, [], [])
        assert result["updated_risk_score"] == 0.65
        assert result["confidence"] == 0.8

    def test_review_retries_then_raises(self, monkeypatch):
        class FailingSession:
            def post(self, url, json, timeout):
                raise TimeoutError("network timeout")

        client = GeminiClient("dummy-key")
        monkeypatch.setattr(client, "session", FailingSession())

        with pytest.raises(GeminiError):
            client.review({}, 0.0, [], [])
