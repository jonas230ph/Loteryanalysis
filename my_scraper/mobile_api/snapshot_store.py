"""Storage adapters for the mobile API's generated lottery snapshot."""

import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

from mobile_api.services.analysis_service import AnalysisService
from mobile_api.services.results_service import ResultsService


class SnapshotUnavailableError(RuntimeError):
    """Raised when the published mobile snapshot cannot be loaded."""


class FileSnapshotStore:
    """Builds a mobile snapshot from local scraper and analysis output files."""

    def __init__(self, project_root):
        self.project_root = Path(project_root)
        self.results_service = ResultsService(self.project_root)
        self.analysis_service = AnalysisService(self.project_root)

    def load(self):
        # This keeps simulator and command-line development independent of cloud
        # credentials while producing the exact same payload as Supabase.
        results = self.results_service.list_results()
        games = self.results_service.list_games()
        return {
            "results": results,
            "games": games,
            "suggestions": self.analysis_service.list_suggestions(),
            "analysis_by_game": {
                game: self.analysis_service.analysis_for_game(game)
                for game in games
            },
        }


class SupabaseSnapshotStore:
    """Reads and writes the one current mobile snapshot in Supabase Postgres."""

    def __init__(self, project_url, api_key, opener=urlopen):
        self.project_url = project_url.rstrip("/")
        self.api_key = api_key
        self.opener = opener

    def load(self):
        # The Koyeb API only needs public read access to this prepared JSON
        # document. The service-role key is never used on the request path.
        request = Request(
            f"{self.project_url}/rest/v1/mobile_snapshots?id=eq.current&select=payload",
            headers=self._headers(),
        )
        try:
            with self.opener(request, timeout=15) as response:
                rows = json.loads(response.read().decode("utf-8"))
        except Exception as exc:
            raise SnapshotUnavailableError("Unable to load the mobile data snapshot") from exc

        if not isinstance(rows, list) or not rows or not isinstance(rows[0].get("payload"), dict):
            raise SnapshotUnavailableError("No published mobile data snapshot is available")
        return rows[0]["payload"]

    def publish(self, snapshot):
        # GitHub Actions uses the service-role key to atomically replace the
        # current snapshot after the scraper and analyzer finish successfully.
        body = json.dumps({
            "id": "current",
            "payload": snapshot,
            "refreshed_at": datetime.now(timezone.utc).isoformat(),
        }).encode("utf-8")
        request = Request(
            f"{self.project_url}/rest/v1/mobile_snapshots?on_conflict=id",
            data=body,
            headers={
                **self._headers(),
                "Content-Type": "application/json",
                "Prefer": "resolution=merge-duplicates,return=minimal",
            },
            method="POST",
        )
        try:
            with self.opener(request, timeout=30):
                return
        except Exception as exc:
            raise SnapshotUnavailableError("Unable to publish the mobile data snapshot") from exc

    def _headers(self):
        return {
            "apikey": self.api_key,
            "Authorization": f"Bearer {self.api_key}",
        }
