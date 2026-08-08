import json
from datetime import datetime
from pathlib import Path


def _parse_draw_date(value):
    # Convert PCSO's mm/dd/yyyy text into ISO format so sorting is reliable.
    parsed = datetime.strptime(value, "%m/%d/%Y")
    return parsed.date().isoformat()


class ResultsService:
    """Loads scraped PCSO draw results from pcso_results.json."""

    def __init__(self, project_root):
        self.project_root = Path(project_root)
        self.results_path = self.project_root / "pcso_results.json"

    def list_results(self):
        # The scraper writes one JSON file; the API normalizes it before the app
        # sees the data.
        if not self.results_path.exists():
            raise FileNotFoundError(f"Missing results file: {self.results_path}")

        records = json.loads(self.results_path.read_text(encoding="utf-8"))
        normalized = [self._normalize_record(record) for record in records]
        return sorted(normalized, key=lambda row: row["draw_date"], reverse=True)

    def list_games(self):
        # Use a set to remove duplicates, then sort for a stable picker/list.
        return sorted({row["lotto_game"] for row in self.list_results()})

    def results_for_game(self, game):
        # Detail screens reuse the normalized list and filter by exact game name.
        return [row for row in self.list_results() if row["lotto_game"] == game]

    def _normalize_record(self, record):
        # Defensive string cleanup prevents blank spaces from leaking into Swift
        # labels or breaking date parsing.
        return {
            "lotto_game": str(record.get("lotto_game", "")).strip(),
            "combinations": str(record.get("combinations", "")).strip(),
            "draw_date": _parse_draw_date(str(record.get("draw_date", "")).strip()),
            "jackpot": str(record.get("jackpot", "")).strip(),
            "winners": str(record.get("winners", "")).strip(),
        }
