import io
import json

import pytest

from app.services.ingestion import IngestionError, IngestionService


def _csv_bytes(content: str) -> io.BytesIO:
    return io.BytesIO(content.encode("utf-8"))


def _patch_gemini(monkeypatch, result=None, raise_on_call=None):
    class Client:
        def review(self, *args, **kwargs):
            if raise_on_call:
                raise raise_on_call
            return result

    monkeypatch.setattr("app.services.scoring.get_gemini_client", lambda: Client())


class TestIngestionService:
    def test_from_csv_parses_valid_rows(self):
        csv = (
            "transactionId,transactionDate,transactionType,amount,currency,"
            "senderName,senderCountry,receiverName,receiverCountry\n"
            "TX-001,2026-10-19,wire,500.00,USD,John Smith,US,Jane Doe,US\n"
        )
        records = IngestionService.from_csv(_csv_bytes(csv))
        assert len(records) == 1
        assert records[0]["transactionId"] == "TX-001"
        assert records[0]["amount"] == 500.0
        assert records[0]["currency"] == "USD"

    def test_from_records_cleans_and_validates(self):
        records = [
            {
                "transactionId": "TX-1",
                "transactionDate": "2026-10-19",
                "transactionType": "wire",
                "amount": "1000",
                "currency": "eur",
                "senderName": "Alice",
                "senderCountry": "DE",
                "receiverName": "Bob",
                "receiverCountry": "FR",
            }
        ]
        cleaned = IngestionService.from_records(records)
        assert cleaned[0]["currency"] == "EUR"
        assert cleaned[0]["amount"] == 1000.0

    def test_missing_required_field_raises(self):
        records = [
            {
                "transactionId": "TX-1",
                "amount": 100,
                "currency": "USD",
                "senderName": "A",
                "senderCountry": "US",
                "receiverName": "B",
                "receiverCountry": "US",
            }
        ]
        with pytest.raises(IngestionError) as exc_info:
            IngestionService.from_records(records)
        assert "transactionDate" in str(exc_info.value)
        assert "transactionType" in str(exc_info.value)

    def test_invalid_amount_raises(self):
        records = [
            {
                "transactionId": "TX-1",
                "transactionDate": "2026-10-19",
                "transactionType": "wire",
                "amount": "not-a-number",
                "currency": "USD",
                "senderName": "A",
                "senderCountry": "US",
                "receiverName": "B",
                "receiverCountry": "US",
            }
        ]
        with pytest.raises(IngestionError) as exc_info:
            IngestionService.from_records(records)
        assert "amount must be a number" in str(exc_info.value)

    def test_validate_records_summary(self):
        records = [
            {"transactionId": "TX-1", "transactionDate": "2026-10-19"},
            {
                "transactionId": "TX-2",
                "transactionDate": "2026-10-19",
                "transactionType": "wire",
                "amount": 100,
                "currency": "USD",
                "senderName": "A",
                "senderCountry": "US",
                "receiverName": "B",
                "receiverCountry": "US",
            },
        ]
        summary = IngestionService.validate_records(records)
        assert summary["total"] == 2
        assert summary["valid"] == 1
        assert summary["invalid"] == 1
        assert summary["errors"][0]["row"] == 1


class TestImportEndpoints:
    def test_import_sample_returns_records(self, client):
        response = client.get("/api/import/sample")
        assert response.status_code == 200
        data = response.get_json()
        assert data["count"] == 4
        assert data["records"][0]["transactionId"] == "TX-001"

    def test_import_csv_validates_and_returns_records(self, client):
        csv = (
            "transactionId,transactionDate,transactionType,amount,currency,"
            "senderName,senderCountry,receiverName,receiverCountry\n"
            "TX-CSV-1,2026-10-19,wire,100,USD,A,US,B,US\n"
        )
        response = client.post(
            "/api/import/csv",
            data={"file": (io.BytesIO(csv.encode("utf-8")), "test.csv")},
            content_type="multipart/form-data",
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data["count"] == 1
        assert data["records"][0]["transactionId"] == "TX-CSV-1"

    def test_import_csv_can_screen(self, client, monkeypatch):
        _patch_gemini(monkeypatch, result={"updated_risk_score": 0.0})
        csv = (
            "transactionId,transactionDate,transactionType,amount,currency,"
            "senderName,senderCountry,receiverName,receiverCountry\n"
            "TX-CSV-2,2026-10-19,wire,50,USD,A,US,B,US\n"
        )
        response = client.post(
            "/api/import/csv?screen=true",
            data={"file": (io.BytesIO(csv.encode("utf-8")), "test.csv")},
            content_type="multipart/form-data",
        )
        assert response.status_code == 200
        data = response.get_json()
        assert "results" in data
        assert data["results"][0]["classification"] == "No Match / Low Risk"

    def test_import_single_validates_and_screens(self, client, monkeypatch):
        _patch_gemini(monkeypatch, result={"updated_risk_score": 0.0})
        payload = {
            "transactionId": "TX-SINGLE-1",
            "transactionDate": "2026-10-19",
            "transactionType": "wire",
            "amount": 100,
            "currency": "USD",
            "senderName": "A",
            "senderCountry": "US",
            "receiverName": "B",
            "receiverCountry": "US",
        }
        response = client.post("/api/import/single", json=payload)
        assert response.status_code == 200
        data = response.get_json()
        assert data["transaction_id"] == "TX-SINGLE-1"

    def test_import_validate_endpoint_csv(self, client):
        csv = (
            "transactionId,transactionDate,transactionType,amount,currency,"
            "senderName,senderCountry,receiverName,receiverCountry\n"
            "TX-V-1,2026-10-19,wire,bad,USD,A,US,B,US\n"
            "TX-V-2,2026-10-19,wire,100,USD,A,US,B,US\n"
        )
        response = client.post(
            "/api/import/validate",
            data={"file": (io.BytesIO(csv.encode("utf-8")), "test.csv")},
            content_type="multipart/form-data",
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data["total"] == 2
        assert data["valid"] == 1
        assert data["invalid"] == 1


class TestBatchEndpointValidation:
    def test_batch_csv_with_bad_amount_returns_400(self, client):
        csv = (
            "transactionId,transactionDate,transactionType,amount,currency,"
            "senderName,senderCountry,receiverName,receiverCountry\n"
            "TX-BAD,2026-10-19,wire,NaN,USD,A,US,B,US\n"
        )
        response = client.post(
            "/api/screen/batch",
            data={"file": (io.BytesIO(csv.encode("utf-8")), "bad.csv")},
            content_type="multipart/form-data",
        )
        assert response.status_code == 400

    def test_batch_json_list_still_works(self, client, monkeypatch):
        _patch_gemini(monkeypatch, result={"updated_risk_score": 0.0})
        transactions = [
            {
                "transactionId": "TX-B-1",
                "transactionDate": "2026-10-19",
                "transactionType": "wire",
                "amount": 50,
                "currency": "USD",
                "senderName": "A",
                "senderCountry": "US",
                "receiverName": "B",
                "receiverCountry": "US",
            }
        ]
        response = client.post("/api/screen/batch", json=transactions)
        assert response.status_code == 200
        data = response.get_json()
        assert data["count"] == 1
        assert data["results"][0]["classification"] == "No Match / Low Risk"

    def test_batch_rejects_non_list_body(self, client):
        response = client.post("/api/screen/batch", json={"not": "a list"})
        assert response.status_code == 400
