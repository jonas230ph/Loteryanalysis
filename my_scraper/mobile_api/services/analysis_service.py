import csv
from pathlib import Path


class AnalysisService:
    def __init__(self, project_root):
        self.project_root = Path(project_root)
        self.output_dir = self.project_root / "analysis_outputs"

    def analysis_for_game(self, game):
        frequency = [
            {
                "number": int(row["numbers"]),
                "frequency": int(row["frequency"]),
            }
            for row in self._read_csv("number_frequency_by_game.csv")
            if row["lotto_game"] == game
        ]
        patterns = [
            {
                "pattern": row["odd_even_pattern"],
                "draws": int(row["draws"]),
            }
            for row in self._read_csv("odd_even_patterns_by_game.csv")
            if row["lotto_game"] == game
        ]
        sum_rows = [
            row for row in self._read_csv("sum_statistics_by_game.csv")
            if row["lotto_game"] == game
        ]

        if not frequency and not patterns and not sum_rows:
            return {
                "lotto_game": game,
                "number_frequency": [],
                "odd_even_patterns": [],
                "sum_statistics": None,
            }

        return {
            "lotto_game": game,
            "number_frequency": frequency,
            "odd_even_patterns": patterns,
            "sum_statistics": self._normalize_sum_stats(sum_rows[0]) if sum_rows else None,
        }

    def list_suggestions(self):
        return [
            {
                "lotto_game": row["lotto_game"],
                "suggested_combination": row["suggested_combination"],
                "sum": int(float(row["sum"])),
                "odd_even_pattern": row["odd_even_pattern"],
                "historical_frequency_score": int(float(row["historical_frequency_score"])),
                "basis": row["basis"],
            }
            for row in self._read_csv("possible_winning_numbers_by_game.csv")
        ]

    def _read_csv(self, filename):
        path = self.output_dir / filename
        if not path.exists():
            raise FileNotFoundError(f"Missing analysis file: {path}")
        with path.open(newline="", encoding="utf-8") as file:
            return list(csv.DictReader(file))

    def _normalize_sum_stats(self, row):
        return {
            "count": int(float(row["count"])),
            "min": float(row["min"]),
            "median": float(row["median"]),
            "mean": float(row["mean"]),
            "max": float(row["max"]),
            "std": float(row["std"]),
        }
