# FlightDelay: FlightAware Cancelled Flights API

## 1. Executive Summary

**Quick verdict: Requires permission for scraping; use official AeroAPI.** FlightAware's Terms of Use restrict automated website access and scraping except through FlightAware data feeds and APIs, and `robots.txt` disallows several automated paths under `/live`. This project therefore provides a production-ready **AeroAPI wrapper** and keeps public-page scraping out of the recommended workflow.

Primary implementation:

```text
/Users/jonasodones/Desktop/src/Flightdelay/api
```

Legacy VBA module:

```text
/Users/jonasodones/Desktop/src/Flightdelay/FlightAwareScraper.bas
```

The VBA scraper exists from the earlier prototype, but the recommended and compliant path is the API wrapper in `api/`.

## 2. What Was Checked

- **Public API documentation:** FlightAware AeroAPI is the official product for flight status and tracking data: `https://www.flightaware.com/commercial/aeroapi/`
- **AeroAPI portal:** API keys are managed through `https://www.flightaware.com/aeroapi/portal/`
- **robots.txt:** `https://www.flightaware.com/robots.txt` includes disallows for multiple automated paths, including `/live/flight/id/` and other non-public automation-sensitive areas.
- **Terms of Use:** `https://www.flightaware.com/about/termsofuse` says automated retrieval/scraping is not allowed except through FlightAware data feeds and APIs.
- **Authentication:** AeroAPI requires the `x-apikey` header. The public website may use cookies/session behavior and should not be automated unless FlightAware grants permission.
- **Rate limits:** Use your AeroAPI plan limits. The wrapper includes cache TTL and retry/backoff for `429` and `5xx` responses.

## 3. Recommended Endpoint

This project wraps:

```text
GET https://aeroapi.flightaware.com/aeroapi/flights/search/advanced
Header: x-apikey: YOUR_AEROAPI_KEY
Query:  {true cancelled} {orig_or_dest {KLAX}}
```

The local REST wrapper exposes:

```text
GET /cancelled?airport=XXX&date=YYYY-MM-DD&airline=YYY&limit=50&format=json
```

Parameters:

- `airport`: optional IATA or ICAO; ICAO is preferred.
- `airline`: optional IATA, ICAO, or airline/operator name.
- `date`: optional `YYYY-MM-DD`; defaults to today.
- `time_window`: optional label such as `00:00-23:59`.
- `limit`: optional, default `50`, maximum `500`.
- `format`: `json` by default; `csv` is also supported.

## 4. Quick Start

```bash
cd /Users/jonasodones/Desktop/src/Flightdelay/api
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export FLIGHTAWARE_API_KEY="YOUR_AEROAPI_KEY"
uvicorn app:app --reload --port 8000
```

Test the API:

```bash
curl "http://127.0.0.1:8000/health"
curl "http://127.0.0.1:8000/cancelled?airport=KLAX&date=2026-05-09&limit=50"
curl "http://127.0.0.1:8000/cancelled?airline=AA&format=csv"
```

Python client example:

```python
import requests

response = requests.get(
    "http://127.0.0.1:8000/cancelled",
    params={"airport": "KLAX", "airline": "AA", "limit": 50},
    timeout=30,
)
response.raise_for_status()
print(response.json())
```

## 5. Environment Variables

Create a `.env` or export these variables in your shell:

```bash
export DATA_MODE=official
export FLIGHTAWARE_API_KEY="YOUR_AEROAPI_KEY"
export AEROAPI_BASE_URL="https://aeroapi.flightaware.com/aeroapi/"
export CACHE_TTL_SECONDS=600
export USER_AGENT="cancelled-flight-api/1.0 contact=ops@example.com"
export LOG_LEVEL=INFO
```

Do not commit real API keys. Use `.env.example` as the template.

## 6. Response Schema

Each cancelled flight is normalized to:

```json
{
  "flight_number": "AAL123",
  "airline": {"name": "American Airlines", "iata": "AA", "icao": "AAL"},
  "origin": {"airport_name": null, "iata": "LAX", "icao": "KLAX", "city": "Los Angeles"},
  "destination": {"airport_name": null, "iata": "DFW", "icao": "KDFW", "city": "Dallas-Fort Worth"},
  "scheduled_departure": "2026-05-09T13:00:00Z",
  "scheduled_arrival": "2026-05-09T16:00:00Z",
  "cancellation_time": null,
  "cancellation_reason": "Cancelled",
  "status_source": "FlightAware AeroAPI",
  "scraped_at": "2026-05-09T04:00:00+00:00",
  "raw_html_snippet": null
}
```

Error example:

```json
{
  "detail": "Missing FLIGHTAWARE_API_KEY environment variable"
}
```

## 7. Tests

The test suite mocks AeroAPI and does not call FlightAware live services.

```bash
cd /Users/jonasodones/Desktop/src/Flightdelay/api
source .venv/bin/activate
pytest -q
```

Current test coverage:

- Airport filter query.
- Airline filter query.
- CSV output path.

Last local result:

```text
3 passed in 0.09s
```

## 8. Docker

```bash
cd /Users/jonasodones/Desktop/src/Flightdelay/api
docker build -t cancelled-flights-api .
docker run --rm -p 8000:8000 \
  -e FLIGHTAWARE_API_KEY="$FLIGHTAWARE_API_KEY" \
  -e DATA_MODE=official \
  cancelled-flights-api
```

## 9. Periodic Sync

Example cron job, every 10 minutes:

```cron
*/10 * * * * curl -s "http://127.0.0.1:8000/cancelled?airport=KLAX&limit=100" > /var/tmp/cancelled_klax.json
```

For production, use a scheduler or queue worker and a persistent cache such as Redis. The included app has an in-process TTL cache controlled by `CACHE_TTL_SECONDS`.

## 10. Legal & Ethical Checklist

Before using this project beyond local testing:

- Confirm your FlightAware AeroAPI plan permits your intended use, storage, redistribution, and volume.
- Do not scrape `https://www.flightaware.com/live/cancelled` unless FlightAware gives written permission.
- Respect AeroAPI rate limits and billing limits.
- Use an identifiable `User-Agent` with a contact address for server-side calls.
- Keep logs of request volume, response status codes, and failures.
- Do not bypass authentication, paywalls, rate limits, robots.txt, or other access controls.
- Do not use the data for safety-critical aviation decisions unless your contract explicitly permits that use.

## 11. Responsible Data Access Audit Template

Use this checklist before adding any new site or data source.

### Required Inputs

- Target website URL and specific page paths.
- Exact data fields wanted.
- Intended use: personal, research, internal business, or commercial.
- Expected volume: requests per minute/hour/day and total records.
- Whether you have an account, API key, license, or written permission.
- Time constraints: real-time, periodic batch, or historical backfill.
- Legal or contractual constraints to consider.

### Audit Output Format

1. **Executive summary:** likely allowed, likely restricted, or permission required.
2. **What was checked:** API docs, robots.txt, Terms of Service, visible public endpoints, authentication, CORS, and rate limits.
3. **Endpoint findings:** method, path, parameters, relevant fields, auth requirement, rate limits, CORS behavior, and whether use appears permitted.
4. **Legal and ethical assessment:** ToS/API license clauses, privacy concerns, redistribution constraints, and whether permission is needed.
5. **Recommended responsible approach:** official API first; scrape only if clearly permitted.
6. **Safe example code:** only for documented or clearly permitted public APIs.
7. **Operational checklist:** low-rate testing, monitoring, backoff, cache, logging, and contact path.
8. **Contact template:** request permission or an API key before scaling.

### Permission Request Template

```text
Subject: Request for API access / data-use permission

Hello,

I am working on a project that needs to retrieve the following data from your service:
[describe fields]

Intended use:
[personal/research/internal/commercial]

Expected volume:
[requests per minute/hour/day and total records]

We would like to use your official API or another approved data-access method. Please let us know the correct endpoint, licensing requirements, attribution requirements, rate limits, pricing, and any restrictions on storage or redistribution.

Thank you,
[name, organization, contact email]
```

## 12. Project Files

```text
Flightdelay/
  README.md
  FlightAwareScraper.bas
  api/
    app.py
    README_API.md
    requirements.txt
    Dockerfile
    .env.example
    pytest.ini
    tests/test_app.py
```

## 13. Next Inputs Needed

To run against real FlightAware data, provide:

- Confirmation that you have an AeroAPI key.
- Your intended use and expected request volume.
- Airports or airlines to query.
- Whether you need recent data only or a historical date range.
