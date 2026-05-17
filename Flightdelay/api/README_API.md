# Cancelled Flights API

## Summary

Use FlightAware AeroAPI, not public-page scraping. FlightAware `robots.txt` restricts several automated paths under `/live`, and the Terms of Use say the website may be accessed only with a human-operated browser except for FlightAware data feeds and APIs. This wrapper therefore defaults to AeroAPI and blocks scrape mode unless your team obtains explicit permission.

## Quick Start

```bash
cd /Users/jonasodones/Desktop/src/Flightdelay/api
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export FLIGHTAWARE_API_KEY="YOUR_AEROAPI_KEY"
uvicorn app:app --reload --port 8000
```

Call the wrapper:

```bash
curl "http://127.0.0.1:8000/cancelled?airport=KLAX&date=2026-05-07&limit=50"
```

CSV:

```bash
curl "http://127.0.0.1:8000/cancelled?airline=AA&format=csv"
```

## AeroAPI Credentials

1. Create or log in to a FlightAware account.
2. Go to the AeroAPI portal: `https://www.flightaware.com/aeroapi/portal/`
3. Create/copy an API key.
4. Store it only in environment variables or a secret manager:

```bash
export FLIGHTAWARE_API_KEY="YOUR_AEROAPI_KEY"
```

FlightAware AeroAPI v4 uses:

```text
Base URL: https://aeroapi.flightaware.com/aeroapi/
Header:   x-apikey: YOUR_AEROAPI_KEY
```

Recommended endpoint for a recent cancelled-flight list:

```text
GET /flights/search/advanced
query={true cancelled} {orig_or_dest {KLAX}}
```

Airport/operator historical and scheduled endpoints may be needed if your AeroAPI plan and use case require date ranges beyond recent search.

## Official AeroAPI Examples

```bash
curl \
  -H "x-apikey: $FLIGHTAWARE_API_KEY" \
  "https://aeroapi.flightaware.com/aeroapi/flights/search/advanced?query=%7Btrue%20cancelled%7D%20%7Borig_or_dest%20%7BKLAX%7D%7D&max_pages=4"
```

```python
import os
import requests

api_key = os.environ["FLIGHTAWARE_API_KEY"]
url = "https://aeroapi.flightaware.com/aeroapi/flights/search/advanced"
params = {"query": "{true cancelled} {orig_or_dest {KLAX}}", "max_pages": 4}
response = requests.get(url, headers={"x-apikey": api_key}, params=params, timeout=30)
response.raise_for_status()
print(response.json())
```

Expected upstream shape, simplified:

```json
{
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
      "status": "Cancelled"
    }
  ]
}
```

## API Spec

```text
GET /cancelled?airport=XXX&date=YYYY-MM-DD&airline=YYY&limit=50&format=json
```

Parameters:

- `airport`: optional IATA or ICAO, but ICAO is preferred by AeroAPI.
- `airline`: optional IATA, ICAO, or name.
- `date`: optional `YYYY-MM-DD`; defaults to today. Current implementation uses AeroAPI recent search and keeps this in the wrapper response for integration consistency.
- `time_window`: optional label such as `00:00-23:59`.
- `limit`: default `50`, max `500`.
- `format`: `json` or `csv`.

## JSON Examples

Complete:

```json
{
  "source": "FlightAware AeroAPI",
  "mode": "official",
  "query": {"airport": "KLAX", "airline": "AA", "date": "2026-05-07", "limit": 50},
  "count": 1,
  "flights": [
    {
      "flight_number": "AAL123",
      "airline": {"name": "American Airlines", "iata": "AA", "icao": "AAL"},
      "origin": {"airport_name": null, "iata": "LAX", "icao": "KLAX", "city": "Los Angeles"},
      "destination": {"airport_name": null, "iata": "DFW", "icao": "KDFW", "city": "Dallas-Fort Worth"},
      "scheduled_departure": "2026-05-07T13:00:00Z",
      "scheduled_arrival": "2026-05-07T16:00:00Z",
      "cancellation_time": null,
      "cancellation_reason": "Cancelled",
      "status_source": "FlightAware AeroAPI",
      "scraped_at": "2026-05-07T04:00:00+00:00",
      "raw_html_snippet": null
    }
  ]
}
```

Partial data:

```json
{
  "count": 1,
  "flights": [
    {
      "flight_number": "DAL456",
      "airline": {"name": "Delta Air Lines", "iata": null, "icao": null},
      "origin": {"airport_name": null, "iata": null, "icao": null, "city": null},
      "destination": {"airport_name": null, "iata": null, "icao": null, "city": null},
      "scheduled_departure": null,
      "scheduled_arrival": null,
      "cancellation_time": null,
      "cancellation_reason": null,
      "status_source": "FlightAware AeroAPI",
      "scraped_at": "2026-05-07T04:00:00+00:00",
      "raw_html_snippet": null
    }
  ]
}
```

Error:

```json
{
  "detail": "Missing FLIGHTAWARE_API_KEY environment variable"
}
```

## Tests

```bash
cd /Users/jonasodones/Desktop/src/Flightdelay/api
pytest -q
```

Scenarios covered:

- Airport filter query.
- Airline filter query.
- CSV response path.

## Docker

```bash
docker build -t cancelled-flights-api .
docker run --rm -p 8000:8000 \
  -e FLIGHTAWARE_API_KEY="$FLIGHTAWARE_API_KEY" \
  -e DATA_MODE=official \
  cancelled-flights-api
```

## Cron Sync Example

Run every 10 minutes and save JSON:

```cron
*/10 * * * * curl -s "http://127.0.0.1:8000/cancelled?airport=KLAX&limit=100" > /var/tmp/cancelled_klax.json
```

For production, prefer a job queue or scheduler and Redis caching instead of in-process cache.

## Legal Checklist

- Confirm your AeroAPI plan permits your intended storage, redistribution, and commercial use.
- Do not scrape `https://www.flightaware.com/live/cancelled` unless FlightAware gives written permission.
- Keep request rates within AeroAPI tier limits.
- Store API keys in environment variables or secret managers, never in source control.
- Do not use this data for safety-critical aviation decisions unless your contract explicitly permits that use.
