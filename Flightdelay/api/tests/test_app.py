import os

import pytest
import respx
from fastapi.testclient import TestClient
from httpx import Response

os.environ["FLIGHTAWARE_API_KEY"] = "test-key"

from app import _cache, app  # noqa: E402


@pytest.fixture()
def client():
    _cache.clear()
    return TestClient(app)


@respx.mock
def test_cancelled_airport_filter(client):
    respx.get("https://aeroapi.flightaware.com/aeroapi/flights/search/advanced").mock(
        return_value=Response(
            200,
            json={
                "flights": [
                    {
                        "ident": "AAL123",
                        "operator": "American Airlines",
                        "operator_iata": "AA",
                        "operator_icao": "AAL",
                        "origin": {"code_iata": "LAX", "code_icao": "KLAX", "city": "Los Angeles"},
                        "destination": {"code_iata": "DFW", "code_icao": "KDFW", "city": "Dallas-Fort Worth"},
                        "scheduled_out": "2026-05-07T13:00:00Z",
                        "scheduled_in": "2026-05-07T16:00:00Z",
                        "status": "Cancelled",
                    }
                ]
            },
        )
    )
    response = client.get("/cancelled?airport=KLAX&limit=1")
    assert response.status_code == 200
    body = response.json()
    assert body["count"] == 1
    assert body["flights"][0]["flight_number"] == "AAL123"


@respx.mock
def test_cancelled_airline_filter(client):
    respx.get("https://aeroapi.flightaware.com/aeroapi/flights/search/advanced").mock(
        return_value=Response(200, json={"flights": [{"ident": "DAL456", "operator": "Delta Air Lines"}]})
    )
    response = client.get("/cancelled?airline=Delta")
    assert response.status_code == 200
    assert response.json()["count"] == 1


@respx.mock
def test_csv_response(client):
    respx.get("https://aeroapi.flightaware.com/aeroapi/flights/search/advanced").mock(
        return_value=Response(200, json={"flights": [{"ident": "AAL123", "operator": "American Airlines"}]})
    )
    response = client.get("/cancelled?airport=KLAX&format=csv")
    assert response.status_code == 200
    assert response.text.startswith("flight_number,")
    assert "AAL123" in response.text
