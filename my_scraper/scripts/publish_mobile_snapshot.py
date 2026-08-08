#!/usr/bin/env python3
"""Publish the latest PCSO scraper outputs as one Supabase mobile snapshot."""

import os
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from mobile_api.snapshot_store import FileSnapshotStore, SupabaseSnapshotStore


def main():
    # Secrets are supplied by GitHub Actions. They are deliberately not read
    # from source files or committed to the repository.
    project_url = os.getenv("SUPABASE_URL")
    service_role_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    if not project_url or not service_role_key:
        print("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY are required", file=sys.stderr)
        return 2

    snapshot = FileSnapshotStore(PROJECT_ROOT).load()
    SupabaseSnapshotStore(project_url, service_role_key).publish(snapshot)
    print("Published PCSO mobile snapshot to Supabase")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
