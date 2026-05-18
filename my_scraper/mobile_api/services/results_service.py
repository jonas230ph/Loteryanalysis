import json
from datetime import datetime
from pathlib import Path


def _parse_draw_date(value):
    parsed = datetime.strptime(value, "%m/%d/%Y")
    return parsed.date().isoformat()


class ResultsService:
    def __init__(self, project_root):
        self.project_root = Path(project_root)
        self.results_path = self.project_root / "pcso_results.json"

    def list_results(self):
        if not self.results_path.exists():
            raise FileNotFoundError(f"Missing results file: {self.results_path}")

        records = json.loads(self.results_path.read_text(encoding="utf-8"))
        normalized = [self._normalize_record(record) for record in records]
        return sorted(normalized, key=lambda row: row["draw_date"], reverse=True)

    def list_games(self):
        return sorted({row["lotto_game"] for row in self.list_results()})

    def results_for_game(self, game):
        return [row for row in self.list_results() if row["lotto_game"] == game]

    def _normalize_record(self, record):
        return {
            "lotto_game": str(record.get("lotto_game", "")).strip(),
            "combinations": str(record.get("combinations", "")).strip(),
            "draw_date": _parse_draw_date(str(record.get("draw_date", "")).strip()),
            "jackpot": str(record.get("jackpot", "")).strip(),
            "winners": str(record.get("winners", "")).strip(),
        }
