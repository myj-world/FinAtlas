import pytest

from app import create_app


@pytest.fixture
def app():
    """Flask application factory for integration tests."""
    return create_app()


@pytest.fixture
def client(app):
    return app.test_client()
