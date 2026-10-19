import pytest

from app.services.gemini import GeminiError
from app.services.scoring import classify_score, screen_transaction


def _make_tx(**overrides):
    defaults = {
        "transactionId": "TX-TEST",
        "transactionDate": "2026-10-19",
        "transactionType": "wire",
        "amount": 100.0,
        "currency": "USD",
        "senderName": "John Doe",
        "senderCountry": "US",
        "receiverName": "Jane Doe",
        "receiverCountry": "US",
    }
    defaults.update(overrides)
    return defaults


class MockGeminiClient:
    def __init__(self, result=None, raise_on_call=None):
        self.result = result
        self.raise_on_call = raise_on_call

    def review(self, transaction, deterministic_score, rules, hits):
        if self.raise_on_call:
            raise self.raise_on_call
        return self.result


@pytest.fixture
def mock_gemini(monkeypatch):
    def _patch(result=None, raise_on_call=None):
        client = MockGeminiClient(result=result, raise_on_call=raise_on_call)
        monkeypatch.setattr("app.services.scoring.get_gemini_client", lambda: client)
        return client

    return _patch


class TestDeterministicScoring:
    def test_no_rules_no_gemini_call(self, mock_gemini):
        patched = mock_gemini(result={"updated_risk_score": 0.99})
        tx = _make_tx()
        result = screen_transaction(tx)

        assert result["deterministic_score"] == 0.0
        assert result["final_score"] == 0.0
        assert result["classification"] == "No Match / Low Risk"
        assert result["gemini_reviewed"] is False
        assert result["gemini_result"] is None
        assert result["sanctions_hits"] == []
        assert result["rules"] == []

    def test_large_transaction_only(self, mock_gemini):
        mock_gemini(result={"updated_risk_score": 0.2})
        tx = _make_tx(amount=1500.0)
        result = screen_transaction(tx)

        assert result["deterministic_score"] == 0.2
        assert result["final_score"] == 0.2
        assert result["classification"] == "No Match / Low Risk"
        assert result["gemini_reviewed"] is True
        assert any(rule["rule"] == "large_transaction" for rule in result["rules"])

    def test_high_risk_jurisdiction_only(self, mock_gemini):
        mock_gemini(result={"updated_risk_score": 0.15})
        tx = _make_tx(receiverCountry="IR")
        result = screen_transaction(tx)

        assert result["deterministic_score"] == 0.15
        assert result["final_score"] == 0.15
        assert result["classification"] == "No Match / Low Risk"
        assert any(rule["rule"] == "high_risk_jurisdiction" for rule in result["rules"])

    def test_sanctions_hit_only(self, mock_gemini):
        mock_gemini(result={"updated_risk_score": 0.5})
        tx = _make_tx(receiverName="Kim Jong Un")
        result = screen_transaction(tx)

        assert result["deterministic_score"] == 0.5
        assert result["final_score"] == 0.5
        assert result["classification"] == "Potential Match / Medium Risk"
        assert result["gemini_reviewed"] is True
        assert len(result["sanctions_hits"]) == 1
        assert result["sanctions_hits"][0]["list"] == "UNSC"

    def test_all_rules_capped_at_one(self, mock_gemini):
        mock_gemini(result={"updated_risk_score": 1.0})
        tx = _make_tx(
            amount=1500.0,
            receiverCountry="IR",
            receiverName="Kim Jong Un",
        )
        result = screen_transaction(tx)

        # With the current weights the deterministic ceiling is 0.85;
        # the cap protects against future weight changes.
        assert result["deterministic_score"] == 0.85
        assert result["final_score"] == 1.0
        assert result["classification"] == "Definite Match / High Risk"
        rules = {rule["rule"] for rule in result["rules"]}
        assert rules == {"sanctions_hit", "large_transaction", "high_risk_jurisdiction"}


class TestGeminiRefinement:
    def test_gemini_refines_score_upwards(self, mock_gemini):
        mock_gemini(result={"updated_risk_score": 0.92})
        tx = _make_tx(receiverName="Kim Jong Un")
        result = screen_transaction(tx)

        assert result["deterministic_score"] == 0.5
        assert result["final_score"] == 0.92
        assert result["classification"] == "Definite Match / High Risk"

    def test_gemini_refines_score_downwards(self, mock_gemini):
        mock_gemini(result={"updated_risk_score": 0.3})
        tx = _make_tx(receiverName="Kim Jong Un")
        result = screen_transaction(tx)

        assert result["deterministic_score"] == 0.5
        assert result["final_score"] == 0.3
        assert result["classification"] == "No Match / Low Risk"

    def test_gemini_failure_raises_error(self, mock_gemini):
        mock_gemini(raise_on_call=GeminiError("Gemini unavailable"))
        tx = _make_tx(amount=1500.0)

        with pytest.raises(GeminiError):
            screen_transaction(tx)


class TestClassification:
    def test_thresholds(self):
        assert classify_score(0.86) == "Definite Match / High Risk"
        assert classify_score(0.85) == "Potential Match / Medium Risk"
        assert classify_score(0.5) == "Potential Match / Medium Risk"
        assert classify_score(0.49) == "No Match / Low Risk"
