from __future__ import annotations

import csv
import html
import io
import logging
import os
import re
import sqlite3
import time
import uuid
from contextlib import asynccontextmanager
from dataclasses import asdict, dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import httpx
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel


LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(level=LOG_LEVEL, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger("flightaware-totals-api")

BASE_URL = "https://www.flightaware.com/live/cancelled"
USER_AGENT = os.getenv("USER_AGENT", "flightaware-totals-api/1.1 contact=ops@example.com")
CACHE_TTL_SECONDS = int(os.getenv("CACHE_TTL_SECONDS", "120"))
STORAGE_BACKEND = os.getenv("STORAGE_BACKEND", "sqlite").lower()
SQLITE_DB_PATH = Path(os.getenv("SQLITE_DB_PATH", "flightaware_scrapes.db"))
SUPABASE_URL = os.getenv("SUPABASE_URL", "").rstrip("/")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
SUPABASE_TABLE = os.getenv("SUPABASE_TABLE", "flightaware_delay_totals")
ENABLE_SCHEDULER = os.getenv("ENABLE_SCHEDULER", "true").lower() in {"1", "true", "yes"}
SCHEDULER_TIMEZONE = os.getenv("SCHEDULER_TIMEZONE", "America/New_York")
SCRAPE_SECRET = os.getenv("SCRAPE_SECRET", "")

PAGE_CONFIG = [
    {"day_offset": 0, "page_label": "today", "path": "/today"},
    {"day_offset": 1, "page_label": "yesterday", "path": "/yesterday"},
    {"day_offset": 2, "page_label": "minus2days", "path": "/minus2days"},
    {"day_offset": 3, "page_label": "minus3days", "path": "/minus3days"},
]

DELAY_RE = re.compile(
    r"Total delays within, into, or out of the United States\s+[^:]*:\s*([0-9][0-9,]*)",
    re.IGNORECASE,
)
CANCELLATION_RE = re.compile(
    r"Total cancellations within, into, or out of the United States\s+[^:]*:\s*([0-9][0-9,]*)",
    re.IGNORECASE,
)

_cache: dict[str, tuple[float, list["DelayTotalsRow"]]] = {}
_scheduler: AsyncIOScheduler | None = None


@dataclass
class DelayTotalsRow:
    run_id: str
    date: str
    day_offset: int
    page_label: str
    total_delays_within_into_or_out_of_united_states: int
    total_cancellations_within_into_or_out_of_united_states: int
    source_url: str
    scraped_at: str


class ScrapeResponse(BaseModel):
    status: str
    storage_backend: str
    run_id: str
    count: int
    rows: list[dict[str, Any]]


@asynccontextmanager
async def lifespan(_app: FastAPI):
    initialize_storage()
    start_scheduler()
    try:
        yield
    finally:
        stop_scheduler()


app = FastAPI(title="FlightAware Delay Totals API", version="1.1.0", lifespan=lifespan)


@app.get("/health")
def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "storage_backend": STORAGE_BACKEND,
        "scheduler_enabled": ENABLE_SCHEDULER,
        "scheduler_timezone": SCHEDULER_TIMEZONE,
    }


@app.post("/flightaware/scrape", response_model=ScrapeResponse)
async def scrape_now(secret: str | None = Query(default=None, description="Optional SCRAPE_SECRET")) -> dict[str, Any]:
    require_scrape_secret(secret)
    rows = await scrape_and_store()
    return {
        "status": "ok",
        "storage_backend": STORAGE_BACKEND,
        "run_id": rows[0].run_id if rows else "",
        "count": len(rows),
        "rows": [asdict(row) for row in rows],
    }


@app.get("/flightaware/totals")
async def get_totals(
    run_id: str | None = Query(default=None, description="Specific scrape run id"),
    format: str = Query(default="json", pattern="^(json|csv)$"),
) -> Response:
    rows = await load_rows(run_id=run_id)

    if format == "csv":
        return Response(
            content=totals_to_csv(rows),
            media_type="text/csv; charset=utf-8",
            headers={"Content-Disposition": "attachment; filename=flightaware_delay_totals.csv"},
        )

    return JSONResponse(
        {
            "source": "FlightAware public cancelled flights totals page",
            "storage_backend": STORAGE_BACKEND,
            "count": len(rows),
            "rows": [asdict(row) for row in rows],
        }
    )


@app.get("/excel/flightaware-totals.csv")
async def excel_csv() -> Response:
    rows = await load_rows(run_id=None)
    return Response(
        content=totals_to_csv(rows),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=flightaware_delay_totals.csv"},
    )


@app.get("/flightaware/pages")
def pages() -> dict[str, list[dict[str, Any]]]:
    return {
        "pages": [
            {
                "day_offset": page["day_offset"],
                "page_label": page["page_label"],
                "source_url": f"{BASE_URL}{page['path']}",
            }
            for page in PAGE_CONFIG
        ]
    }


async def scrape_and_store() -> list[DelayTotalsRow]:
    cache_key = "scrape_now"
    cached = _cache.get(cache_key)
    if cached and time.time() - cached[0] < CACHE_TTL_SECONDS:
        return cached[1]

    rows = await scrape_flightaware_pages()
    await save_rows(rows)
    _cache[cache_key] = (time.time(), rows)
    return rows


async def scrape_flightaware_pages() -> list[DelayTotalsRow]:
    run_id = str(uuid.uuid4())
    scraped_at = datetime.now(timezone.utc).isoformat()
    today = datetime.now(ZoneInfo(SCHEDULER_TIMEZONE)).date()
    rows: list[DelayTotalsRow] = []

    async with httpx.AsyncClient(timeout=30, follow_redirects=True, headers={"User-Agent": USER_AGENT}) as client:
        for page in PAGE_CONFIG:
            source_url = f"{BASE_URL}{page['path']}"
            response = await client.get(source_url)
            if response.status_code >= 400:
                raise HTTPException(status_code=502, detail=f"FlightAware returned {response.status_code} for {source_url}")

            rows.append(parse_totals_page(response.text, page, source_url, run_id, scraped_at, today))

    return rows


def parse_totals_page(
    raw_html: str,
    page: dict[str, Any],
    source_url: str,
    run_id: str,
    scraped_at: str,
    today: date,
) -> DelayTotalsRow:
    text = normalize_text(raw_html)
    delay_match = DELAY_RE.search(text)
    cancellation_match = CANCELLATION_RE.search(text)

    if not delay_match or not cancellation_match:
        raise HTTPException(status_code=502, detail=f"Could not find FlightAware US totals on {source_url}")

    target_date = today - timedelta(days=int(page["day_offset"]))
    return DelayTotalsRow(
        run_id=run_id,
        date=target_date.isoformat(),
        day_offset=int(page["day_offset"]),
        page_label=str(page["page_label"]),
        total_delays_within_into_or_out_of_united_states=parse_number(delay_match.group(1)),
        total_cancellations_within_into_or_out_of_united_states=parse_number(cancellation_match.group(1)),
        source_url=source_url,
        scraped_at=scraped_at,
    )


def normalize_text(raw_html: str) -> str:
    text = re.sub(r"<script\b[^<]*(?:(?!</script>)<[^<]*)*</script>", " ", raw_html, flags=re.IGNORECASE)
    text = re.sub(r"<style\b[^<]*(?:(?!</style>)<[^<]*)*</style>", " ", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", html.unescape(text).replace("\u00a0", " ")).strip()


def parse_number(value: str) -> int:
    return int(value.replace(",", ""))


def initialize_storage() -> None:
    if STORAGE_BACKEND == "sqlite":
        initialize_sqlite()
    elif STORAGE_BACKEND == "supabase":
        if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
            raise RuntimeError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY are required when STORAGE_BACKEND=supabase")
    else:
        raise RuntimeError("STORAGE_BACKEND must be sqlite or supabase")


def initialize_sqlite() -> None:
    SQLITE_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(SQLITE_DB_PATH) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS flightaware_delay_totals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT NOT NULL,
                date TEXT NOT NULL,
                day_offset INTEGER NOT NULL,
                page_label TEXT NOT NULL,
                total_delays_within_into_or_out_of_united_states INTEGER NOT NULL,
                total_cancellations_within_into_or_out_of_united_states INTEGER NOT NULL,
                source_url TEXT NOT NULL,
                scraped_at TEXT NOT NULL
            )
            """
        )
        connection.execute("CREATE INDEX IF NOT EXISTS idx_flightaware_run ON flightaware_delay_totals(run_id)")
        connection.execute("CREATE INDEX IF NOT EXISTS idx_flightaware_scraped_at ON flightaware_delay_totals(scraped_at)")


async def save_rows(rows: list[DelayTotalsRow]) -> None:
    if STORAGE_BACKEND == "sqlite":
        save_rows_sqlite(rows)
        return

    await save_rows_supabase(rows)


def save_rows_sqlite(rows: list[DelayTotalsRow]) -> None:
    initialize_sqlite()
    with sqlite3.connect(SQLITE_DB_PATH) as connection:
        connection.executemany(
            """
            INSERT INTO flightaware_delay_totals (
                run_id,
                date,
                day_offset,
                page_label,
                total_delays_within_into_or_out_of_united_states,
                total_cancellations_within_into_or_out_of_united_states,
                source_url,
                scraped_at
            ) VALUES (
                :run_id,
                :date,
                :day_offset,
                :page_label,
                :total_delays_within_into_or_out_of_united_states,
                :total_cancellations_within_into_or_out_of_united_states,
                :source_url,
                :scraped_at
            )
            """,
            [asdict(row) for row in rows],
        )


async def save_rows_supabase(rows: list[DelayTotalsRow]) -> None:
    url = f"{SUPABASE_URL}/rest/v1/{SUPABASE_TABLE}"
    headers = supabase_headers(prefer="return=minimal")
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(url, headers=headers, json=[asdict(row) for row in rows])
        if response.status_code >= 400:
            raise HTTPException(status_code=502, detail=f"Supabase insert failed: {response.text}")


async def load_rows(run_id: str | None) -> list[DelayTotalsRow]:
    if STORAGE_BACKEND == "sqlite":
        return load_rows_sqlite(run_id)

    return await load_rows_supabase(run_id)


def load_rows_sqlite(run_id: str | None) -> list[DelayTotalsRow]:
    initialize_sqlite()
    with sqlite3.connect(SQLITE_DB_PATH) as connection:
        connection.row_factory = sqlite3.Row
        selected_run_id = run_id or latest_sqlite_run_id(connection)
        if not selected_run_id:
            return []

        rows = connection.execute(
            """
            SELECT
                run_id,
                date,
                day_offset,
                page_label,
                total_delays_within_into_or_out_of_united_states,
                total_cancellations_within_into_or_out_of_united_states,
                source_url,
                scraped_at
            FROM flightaware_delay_totals
            WHERE run_id = ?
            ORDER BY day_offset ASC
            """,
            (selected_run_id,),
        ).fetchall()

    return [DelayTotalsRow(**dict(row)) for row in rows]


def latest_sqlite_run_id(connection: sqlite3.Connection) -> str | None:
    row = connection.execute(
        """
        SELECT run_id
        FROM flightaware_delay_totals
        ORDER BY scraped_at DESC, id DESC
        LIMIT 1
        """
    ).fetchone()
    return str(row[0]) if row else None


async def load_rows_supabase(run_id: str | None) -> list[DelayTotalsRow]:
    selected_run_id = run_id or await latest_supabase_run_id()
    if not selected_run_id:
        return []

    url = f"{SUPABASE_URL}/rest/v1/{SUPABASE_TABLE}"
    params = {"run_id": f"eq.{selected_run_id}", "select": "*", "order": "day_offset.asc"}
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.get(url, headers=supabase_headers(), params=params)
        if response.status_code >= 400:
            raise HTTPException(status_code=502, detail=f"Supabase select failed: {response.text}")

    return [DelayTotalsRow(**row) for row in response.json()]


async def latest_supabase_run_id() -> str | None:
    url = f"{SUPABASE_URL}/rest/v1/{SUPABASE_TABLE}"
    params = {"select": "run_id,scraped_at", "order": "scraped_at.desc", "limit": "1"}
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.get(url, headers=supabase_headers(), params=params)
        if response.status_code >= 400:
            raise HTTPException(status_code=502, detail=f"Supabase latest run lookup failed: {response.text}")

    payload = response.json()
    return payload[0]["run_id"] if payload else None


def supabase_headers(prefer: str | None = None) -> dict[str, str]:
    headers = {
        "apikey": SUPABASE_SERVICE_ROLE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
        "Content-Type": "application/json",
    }
    if prefer:
        headers["Prefer"] = prefer
    return headers


def totals_to_csv(rows: list[DelayTotalsRow]) -> str:
    buffer = io.StringIO()
    fieldnames = [
        "date",
        "day_offset",
        "page_label",
        "total_delays_within_into_or_out_of_united_states",
        "total_cancellations_within_into_or_out_of_united_states",
        "source_url",
        "scraped_at",
        "run_id",
    ]
    writer = csv.DictWriter(buffer, fieldnames=fieldnames, lineterminator="\r\n")
    writer.writeheader()
    for row in rows:
        writer.writerow(asdict(row))
    return "\ufeff" + buffer.getvalue()


def start_scheduler() -> None:
    global _scheduler
    if not ENABLE_SCHEDULER:
        return

    scheduler_timezone = ZoneInfo(SCHEDULER_TIMEZONE)
    scheduler = AsyncIOScheduler(timezone=scheduler_timezone)
    for hour, minute, job_id in [(0, 0, "midnight_et"), (5, 0, "five_am_et"), (21, 0, "nine_pm_et")]:
        scheduler.add_job(
            scheduled_scrape,
            CronTrigger(hour=hour, minute=minute, timezone=scheduler_timezone),
            id=f"flightaware_scrape_{job_id}",
            replace_existing=True,
            max_instances=1,
            coalesce=True,
        )
    scheduler.start()
    _scheduler = scheduler
    logger.info("Scheduled FlightAware scrapes at 12:00 AM, 5:00 AM, and 9:00 PM %s", SCHEDULER_TIMEZONE)


def stop_scheduler() -> None:
    global _scheduler
    if _scheduler:
        _scheduler.shutdown(wait=False)
        _scheduler = None


async def scheduled_scrape() -> None:
    try:
        _cache.clear()
        rows = await scrape_and_store()
        logger.info("Scheduled scrape stored %s rows for run %s", len(rows), rows[0].run_id if rows else "")
    except Exception:
        logger.exception("Scheduled scrape failed")


def require_scrape_secret(secret: str | None) -> None:
    if SCRAPE_SECRET and secret != SCRAPE_SECRET:
        raise HTTPException(status_code=401, detail="Invalid scrape secret")
