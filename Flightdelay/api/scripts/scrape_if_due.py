from __future__ import annotations

import asyncio
import os
from datetime import datetime
from zoneinfo import ZoneInfo

os.environ.setdefault("ENABLE_SCHEDULER", "false")

from app import SCHEDULER_TIMEZONE, initialize_storage, scrape_and_store  # noqa: E402


DUE_HOURS_ET = {0, 5, 21}


async def main() -> None:
    now_et = datetime.now(ZoneInfo(SCHEDULER_TIMEZONE))
    if now_et.hour not in DUE_HOURS_ET:
        print(f"Not due at {now_et.isoformat()}; expected ET hours {sorted(DUE_HOURS_ET)}.")
        return

    initialize_storage()
    rows = await scrape_and_store()
    run_id = rows[0].run_id if rows else ""
    print(f"Stored {len(rows)} FlightAware rows for run {run_id} at {now_et.isoformat()}.")


if __name__ == "__main__":
    asyncio.run(main())
