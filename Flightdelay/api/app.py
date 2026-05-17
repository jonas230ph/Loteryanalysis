from __future__ import annotations

import csv
import io
import logging
import os
import time
from datetime import date, datetime, timezone
from typing import Any

import httpx
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, Field


LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(level=LOG_LEVEL, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger("flightaware-cancelled-api")

DATA_MODE = os.getenv("DATA_MODE", "official").lower()
AEROAPI_BASE_URL = os.getenv("AEROAPI_BASE_URL", "https://aeroapi.flightaware.com/aeroapi/")
AEROAPI_KEY = os.getenv("FLIGHTAWARE_API_KEY", "")
CACHE_TTL_SECONDS = int(os.getenv("CACHE_TTL_SECONDS", "600"))
USER_AGENT = os.getenv("USER_AGENT", "cancelled-flight-api/1.0 contact=ops@example.com")

_cache: dict[str, tuple[float, dict[str, Any]]] = {}


class Airport(BaseModel):
    airport_name: str | None = None
    iata: str | None = None
    icao: str | None = None
    city: str | None = None


class Airline(BaseModel):
    name: str | None = None
    iata: str | None = None
    icao: str | None = None


class CancelledFlight(BaseModel):
    flight_number: str
    airline: Airline = Field(default_factory=Airline)
    origin: Airport = Field(default_factory=Airport)
    destination: Airport = Field(default_factory=Airport)
    scheduled_departure: str | None = None
    scheduled_arrival: str | None = None
    cancellation_time: str | None = None
    cancellation_reason: str | None = None
    status_source: str = "FlightAware AeroAPI"
    scraped_at: str
    raw_html_snippet: str | None = None


app = FastAPI(title="Cancelled Flights API", version="1.0.0")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "mode": DATA_MODE}


@app.get("/cancelled")
async def get_cancelled(
    airport: str | None = Query(default=None, description="IATA or ICAO airport code"),
    airline: str | None = Query(default=None, description="IATA, ICAO, or operator/name filter"),
    date_: date | None = Query(default=None, alias="date", description="YYYY-MM-DD; defaults to today"),
    time_window: str | None = Query(default=None, description="Optional app-side label, e.g. 00:00-23:59"),
    limit: int = Query(default=50, ge=1, le=500),
    format: str = Query(default="json", pattern="^(json|csv)$"),
) -> Response:
    target_date = date_ or datetime.now(timezone.utc).date()

    if DATA_MODE != "official":
        raise HTTPException(
            status_code=501,
            detail=(
                "Scrape mode is disabled. FlightAware Terms of Use restrict automated "
                "website scraping; use AeroAPI or obtain written permission."
            ),
        )

    payload = await fetch_cancelled_from_aeroapi(
        airport=airport,
        airline=airline,
        target_date=target_date,
        time_window=time_window,
        limit=limit,
    )
    flights = [CancelledFlight(**item) for item in payload["flights"]]

    if format == "csv":
        return Response(content=to_csv(flights), media_type="text/csv")

    return JSONResponse(
        {
            "source": "FlightAware AeroAPI",
            "mode": DATA_MODE,
            "query": {
                "airport": airport,
                "airline": airline,
                "date": target_date.isoformat(),
                "time_window": time_window,
                "limit": limit,
            },
            "count": len(flights),
            "flights": [flight.model_dump() for flight in flights],
        }
    )


async def fetch_cancelled_from_aeroapi(
    airport: str | None,
    airline: str | None,
    target_date: date,
    time_window: str | None,
    limit: int,
) -> dict[str, Any]:
    if not AEROAPI_KEY:
        raise HTTPException(status_code=500, detail="Missing FLIGHTAWARE_API_KEY environment variable")

    cache_key = f"{airport}|{airline}|{target_date.isoformat()}|{time_window}|{limit}"
    cached = _cache.get(cache_key)
    if cached and time.time() - cached[0] < CACHE_TTL_SECONDS:
        return cached[1]

    raw = await aeroapi_search_cancelled(airport, airline, limit)
    flights = normalize_aeroapi_flights(raw, airline=airline, limit=limit)
    payload = {"flights": flights, "raw_count": len(raw.get("flights", []))}
    _cache[cache_key] = (time.time(), payload)
    return payload


async def aeroapi_search_cancelled(airport: str | None, airline: str | None, limit: int) -> dict[str, Any]:
    query_parts = ["{true cancelled}"]
    if airport:
        query_parts.append(f"{{orig_or_dest {{{airport.upper()}}}}}")
    if airline:
        query_parts.append(f"{{operator {{{airline.upper()}}}}}")

    max_pages = max(1, min(10, (limit + 14) // 15))
    params = {"query": " ".join(query_parts), "max_pages": max_pages}
    headers = {"x-apikey": AEROAPI_KEY, "User-Agent": USER_AGENT}
    url = f"{AEROAPI_BASE_URL.rstrip('/')}/flights/search/advanced"

    async with httpx.AsyncClient(timeout=30) as client:
        for attempt in range(4):
            try:
                response = await client.get(url, headers=headers, params=params)
                if response.status_code in {429, 500, 502, 503, 504}:
                    raise httpx.HTTPStatusError("retryable upstream error", request=response.request, response=response)
                if response.status_code >= 400:
                    raise HTTPException(status_code=response.status_code, detail=response.text)
                return response.json()
            except httpx.HTTPStatusError as exc:
                wait_seconds = 2**attempt
                logger.warning("AeroAPI retry %s after status %s", attempt + 1, exc.response.status_code)
                if attempt == 3:
                    raise HTTPException(status_code=502, detail=f"AeroAPI unavailable: {exc.response.text}") from exc
                await sleep(wait_seconds)
            except httpx.RequestError as exc:
                if attempt == 3:
                    raise HTTPException(status_code=502, detail=f"AeroAPI request failed: {exc}") from exc
                await sleep(2**attempt)

    return {"flights": []}


async def sleep(seconds: int) -> None:
    import asyncio

    await asyncio.sleep(seconds)


def normalize_aeroapi_flights(raw: dict[str, Any], airline: str | None, limit: int) -> list[dict[str, Any]]:
    scraped_at = datetime.now(timezone.utc).isoformat()
    rows: list[dict[str, Any]] = []

    for item in raw.get("flights", []):
        ident = item.get("ident") or item.get("ident_iata") or item.get("fa_flight_id") or ""
        operator = item.get("operator") or ""
        operator_iata = item.get("operator_iata")
        operator_icao = item.get("operator_icao")

        if airline and airline.upper() not in " ".join(
            str(value).upper() for value in [operator, operator_iata, operator_icao, ident]
        ):
            continue

        rows.append(
            {
                "flight_number": ident,
                "airline": {"name": operator or None, "iata": operator_iata, "icao": operator_icao},
                "origin": airport_from_aeroapi(item.get("origin")),
                "destination": airport_from_aeroapi(item.get("destination")),
                "scheduled_departure": item.get("scheduled_out") or item.get("scheduled_off"),
                "scheduled_arrival": item.get("scheduled_in") or item.get("scheduled_on"),
                "cancellation_time": item.get("cancelled_at"),
                "cancellation_reason": item.get("cancellation_reason") or item.get("status"),
                "status_source": "FlightAware AeroAPI",
                "scraped_at": scraped_at,
                "raw_html_snippet": None,
            }
        )

        if len(rows) >= limit:
            break

    return rows


def airport_from_aeroapi(value: dict[str, Any] | None) -> dict[str, str | None]:
    value = value or {}
    return {
        "airport_name": value.get("name") or value.get("airport_name"),
        "iata": value.get("code_iata") or value.get("iata"),
        "icao": value.get("code_icao") or value.get("icao") or value.get("code"),
        "city": value.get("city"),
    }


def to_csv(flights: list[CancelledFlight]) -> str:
    buffer = io.StringIO()
    writer = csv.DictWriter(
        buffer,
        fieldnames=[
            "flight_number",
            "airline_name",
            "airline_iata",
            "airline_icao",
            "origin_iata",
            "origin_icao",
            "destination_iata",
            "destination_icao",
            "scheduled_departure",
            "scheduled_arrival",
            "cancellation_time",
            "cancellation_reason",
            "status_source",
            "scraped_at",
        ],
    )
    writer.writeheader()
    for flight in flights:
        writer.writerow(
            {
                "flight_number": flight.flight_number,
                "airline_name": flight.airline.name,
                "airline_iata": flight.airline.iata,
                "airline_icao": flight.airline.icao,
                "origin_iata": flight.origin.iata,
                "origin_icao": flight.origin.icao,
                "destination_iata": flight.destination.iata,
                "destination_icao": flight.destination.icao,
                "scheduled_departure": flight.scheduled_departure,
                "scheduled_arrival": flight.scheduled_arrival,
                "cancellation_time": flight.cancellation_time,
                "cancellation_reason": flight.cancellation_reason,
                "status_source": flight.status_source,
                "scraped_at": flight.scraped_at,
            }
        )
    return buffer.getvalue()
