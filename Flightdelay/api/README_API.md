# FlightAware Delay Totals API

This FastAPI service scrapes FlightAware's public cancelled-flight totals pages and stores the United States delay/cancellation totals for today and the previous 3 days.

It captures these 2 values from each source page:

- `Total delays within, into, or out of the United States ...`
- `Total cancellations within, into, or out of the United States ...`

## Source Pages

The scraper reads these pages:

```text
https://www.flightaware.com/live/cancelled/today
https://www.flightaware.com/live/cancelled/yesterday
https://www.flightaware.com/live/cancelled/minus2days
https://www.flightaware.com/live/cancelled/minus3days
```

## Schedule

The intended scrape schedule is:

- `12:00 AM ET`
- `5:00 AM ET`
- `9:00 PM ET`

For local or always-on hosting, the app can use its built-in scheduler with `America/New_York`, so daylight saving time is handled as ET rather than fixed UTC offset EST.

For Render, the included `render.yaml` uses a cron service that runs hourly. The cron service runs `scripts/scrape_if_due.py`; that script checks the current `America/New_York` hour and only scrapes at `00`, `05`, and `21`. This avoids Render's UTC-only cron schedule drifting during daylight saving time.

## Requirements

- Python 3.12+
- Internet access to `https://www.flightaware.com`
- FastAPI dependencies from `requirements.txt`
- Storage:
  - Default: SQLite
  - Optional: Supabase table using `supabase_schema.sql`

No FlightAware API key is required for this public totals scraper.

## Local Setup

```bash
cd /Users/jonasodones/Desktop/src/Flightdelay/api
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app:app --reload --port 8000
```

Open:

```text
http://127.0.0.1:8000/health
```

## Run A Scrape

```bash
curl -X POST "http://127.0.0.1:8000/flightaware/scrape"
```

Response shape:

```json
{
  "status": "ok",
  "storage_backend": "sqlite",
  "run_id": "uuid",
  "count": 4,
  "rows": []
}
```

## Read Latest Stored Data

JSON:

```bash
curl "http://127.0.0.1:8000/flightaware/totals"
```

CSV:

```bash
curl "http://127.0.0.1:8000/flightaware/totals?format=csv"
```

Excel-friendly CSV endpoint:

```text
http://127.0.0.1:8000/excel/flightaware-totals.csv
```

CSV columns:

```csv
date,day_offset,page_label,total_delays_within_into_or_out_of_united_states,total_cancellations_within_into_or_out_of_united_states,source_url,scraped_at,run_id
```

## Add To Excel

1. Start the API locally or deploy it.
2. Copy the CSV URL:

```text
http://127.0.0.1:8000/excel/flightaware-totals.csv
```

3. In Excel, choose **Data**.
4. Choose **From Web**.
5. Paste the CSV URL.
6. Load the table.
7. To refresh later, use **Data > Refresh All**.

If deployed on Render, use your Render URL:

```text
https://YOUR-RENDER-SERVICE.onrender.com/excel/flightaware-totals.csv
```

## Environment Variables

```text
STORAGE_BACKEND=sqlite
SQLITE_DB_PATH=flightaware_scrapes.db
ENABLE_SCHEDULER=true
SCHEDULER_TIMEZONE=America/New_York
CACHE_TTL_SECONDS=120
SCRAPE_SECRET=
USER_AGENT=flightaware-totals-api/1.1 contact=ops@example.com
LOG_LEVEL=INFO
```

Optional Supabase settings:

```text
STORAGE_BACKEND=supabase
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key
SUPABASE_TABLE=flightaware_delay_totals
```

If `SCRAPE_SECRET` is set, manual scrape calls must include it:

```bash
curl -X POST "https://YOUR-SERVICE/flightaware/scrape?secret=YOUR_SECRET"
```

## SQLite Storage

SQLite is the default storage backend.

For local use:

```text
SQLITE_DB_PATH=flightaware_scrapes.db
```

For Render, use a persistent disk:

```text
SQLITE_DB_PATH=/var/data/flightaware_scrapes.db
```

Without a persistent disk on Render, SQLite data can disappear after restarts.

## Supabase Storage

1. Create a Supabase project.
2. Open Supabase SQL Editor.
3. Run `supabase_schema.sql`.
4. Set these environment variables:

```text
STORAGE_BACKEND=supabase
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key
SUPABASE_TABLE=flightaware_delay_totals
```

Use the service role key only on the server. Do not expose it in browser code.

## Deploy To Render + Supabase

Recommended production setup:

- Render Web Service for the API.
- Supabase for durable storage.
- Render Cron Job for scheduled scraping.
- GitHub Actions for tests before deploy.

### 1. Create Supabase Table

1. Create or open your Supabase project.
2. Open **SQL Editor**.
3. Run the SQL in:

```text
Flightdelay/api/supabase_schema.sql
```

4. Copy these values from Supabase:

```text
SUPABASE_URL
SUPABASE_SERVICE_ROLE_KEY
```

Use the service role key only in Render server-side environment variables. Do not put it in browser code.

### 2. Deploy Render Blueprint

1. Push this repository to GitHub.
2. In Render, choose **New > Blueprint**.
3. Select the repo.
4. Use `Flightdelay/api/render.yaml`.
5. Render will ask for secret values marked `sync: false`.
6. Enter:

```text
SUPABASE_URL
SUPABASE_SERVICE_ROLE_KEY
```

7. Deploy the Blueprint.

The Blueprint creates:

- `flightaware-delay-totals-api`: the web API.
- `flightaware-delay-totals-scrape-scheduler`: an hourly cron job that scrapes only at `12:00 AM ET`, `5:00 AM ET`, and `9:00 PM ET`.

### 3. Configure Render Auto Deploy

Render supports auto-deploy on commit, or deploy only after checks pass. For this project, use **checksPass** if available in your Render service settings so GitHub Actions tests pass before deployment.

The GitHub Actions workflow is:

```text
.github/workflows/flightaware-api-tests.yml
```

### Manual Render Web Service Setup

1. In Render, choose **New > Web Service**.
2. Root directory:

```text
Flightdelay/api
```

3. Build command:

```bash
pip install -r requirements.txt
```

4. Start command:

```bash
uvicorn app:app --host 0.0.0.0 --port $PORT
```

5. Set environment variables:

```text
STORAGE_BACKEND=supabase
ENABLE_SCHEDULER=false
SCHEDULER_TIMEZONE=America/New_York
SUPABASE_URL=your Supabase URL
SUPABASE_SERVICE_ROLE_KEY=your Supabase service role key
SUPABASE_TABLE=flightaware_delay_totals
SCRAPE_SECRET=any long random secret
```

6. Create a Render Cron Job using the same repo and root directory:

```text
Flightdelay/api
```

7. Cron build command:

```bash
pip install -r requirements.txt
```

8. Cron start command:

```bash
python scripts/scrape_if_due.py
```

9. Cron schedule:

```text
0 * * * *
```

Render cron schedules use UTC. The hourly schedule is intentional; `scripts/scrape_if_due.py` checks New York time and exits without scraping unless the current ET hour is `00`, `05`, or `21`.

## API Endpoints

```text
GET  /health
GET  /flightaware/pages
POST /flightaware/scrape
GET  /flightaware/totals
GET  /flightaware/totals?format=csv
GET  /excel/flightaware-totals.csv
```

## Tests

```bash
cd /Users/jonasodones/Desktop/src/Flightdelay/api
.venv/bin/python -m pytest -q
```

## Important Notes

- The service scrapes 4 pages per run.
- Avoid running the scraper repeatedly in a tight loop.
- FlightAware can change the page text or block automated requests; if that happens, the parser may need an update.
- For production or commercial usage, confirm that your use of FlightAware page data is allowed by FlightAware's current terms.
