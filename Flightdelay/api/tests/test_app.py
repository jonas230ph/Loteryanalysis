import os
from pathlib import Path

import pytest
import respx
from fastapi.testclient import TestClient
from httpx import Response

os.environ["ENABLE_SCHEDULER"] = "false"
os.environ["STORAGE_BACKEND"] = "sqlite"
os.environ["SQLITE_DB_PATH"] = "/tmp/flightaware_test_scrapes.db"

from app import _cache, app  # noqa: E402


SAMPLE_HTML = """
<html>
  <body>
    Total delays within, into, or out of the United States today: 3,121
    Total cancellations within, into, or out of the United States today: 93
  </body>
</html>
"""


@pytest.fixture()
def client():
    _cache.clear()
    db_path = Path(os.environ["SQLITE_DB_PATH"])
    if db_path.exists():
        db_path.unlink()

    with TestClient(app) as test_client:
        yield test_client

    _cache.clear()
    if db_path.exists():
        db_path.unlink()


def mock_flightaware_pages():
    for path in ["/today", "/yesterday", "/minus2days", "/minus3days"]:
        respx.get(f"https://www.flightaware.com/live/cancelled{path}").mock(return_value=Response(200, text=SAMPLE_HTML))


@respx.mock
def test_scrape_stores_four_rows(client):
    mock_flightaware_pages()

    response = client.post("/flightaware/scrape")

    assert response.status_code == 200
    body = response.json()
    assert body["count"] == 4
    assert body["rows"][0]["page_label"] == "today"
    assert body["rows"][0]["total_delays_within_into_or_out_of_united_states"] == 3121
    assert body["rows"][0]["total_cancellations_within_into_or_out_of_united_states"] == 93


@respx.mock
def test_latest_totals_returns_last_scrape(client):
    mock_flightaware_pages()
    client.post("/flightaware/scrape")

    response = client.get("/flightaware/totals")

    assert response.status_code == 200
    body = response.json()
    assert body["count"] == 4
    assert body["rows"][3]["page_label"] == "minus3days"


@respx.mock
def test_excel_csv_contains_cancellations(client):
    mock_flightaware_pages()
    client.post("/flightaware/scrape")

    response = client.get("/excel/flightaware-totals.csv")

    assert response.status_code == 200
    assert response.text.startswith("\ufeffdate,")
    assert "total_cancellations_within_into_or_out_of_united_states" in response.text
    assert ",93," in response.text
