import pytest

from app.services.sanctions import SanctionsRepository, sanctions_repo
from app.utils import normalize_name


@pytest.fixture(autouse=True)
def reload_repo(monkeypatch):
    """Ensure a fresh repository instance for every sanctions test."""
    fresh = SanctionsRepository()
    monkeypatch.setattr("app.services.sanctions.sanctions_repo", fresh)
    fresh.load()


class TestSanctionsRepository:
    def test_loads_all_three_lists(self):
        stats = sanctions_repo.stats()
        assert set(stats.keys()) == {"UNSC", "EU", "OFAC"}
        assert all(count > 0 for count in stats.values())

    def test_exact_name_match(self):
        hits = sanctions_repo.match("Kim Jong Un")
        assert len(hits) == 1
        assert hits[0]["list"] == "UNSC"
        assert hits[0]["entity_id"] == "UNSC-1"

    def test_alias_match(self):
        hits = sanctions_repo.match("El Chapo")
        assert len(hits) == 1
        assert hits[0]["list"] == "OFAC"
        assert hits[0]["entity_id"] == "OFAC-1"

    def test_normalised_name_match(self):
        # Punctuation and case differences collapse to the same key.
        hits = sanctions_repo.match("kim jong-un")
        assert len(hits) == 1
        assert hits[0]["list"] == "UNSC"

    def test_no_match_returns_empty_list(self):
        assert sanctions_repo.match("John Doe") == []

    def test_empty_name_returns_empty_list(self):
        assert sanctions_repo.match("") == []
        assert sanctions_repo.match(None) == []

    def test_name_normalization_helper(self):
        assert normalize_name("  El   Chapo! ") == "elchapo"
        assert normalize_name("Lukashenka, Alyaksandr") == "lukashenkaalyaksandr"
