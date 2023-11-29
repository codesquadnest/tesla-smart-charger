"""
Tests for the fastapi app.
"""

import pytest

from fastapi.testclient import TestClient

from tesla_smart_charger.main import app


@pytest.fixture
def client():
    """
    Create a test client for the fastapi app.
    """
    return TestClient(app)


def test_read_root(client):
    """
    Test the root endpoint.
    """
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"Hello": "World"}



