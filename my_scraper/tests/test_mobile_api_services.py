import json
import tempfile
import unittest
from pathlib import Path

from mobile_api.services.results_service import ResultsService


class ResultsServiceTests(unittest.TestCase):
    def test_loads_results_sorted_newest_first_and_lists_games(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "pcso_results.json").write_text(json.dumps([
                {
                    "lotto_game": "Lotto 6/42",
                    "combinations": "01-02-03-04-05-06",
                    "draw_date": "5/1/2026",
                    "jackpot": "10,000,000.00",
                    "winners": "0",
                },
                {
                    "lotto_game": "Ultra Lotto 6/58",
                    "combinations": "10-11-12-13-14-15",
                    "draw_date": "5/3/2026",
                    "jackpot": "50,000,000.00",
                    "winners": "1",
                },
            ]), encoding="utf-8")

            service = ResultsService(root)

            self.assertEqual(
                [row["lotto_game"] for row in service.list_results()],
                ["Ultra Lotto 6/58", "Lotto 6/42"],
            )
            self.assertEqual(service.list_games(), ["Lotto 6/42", "Ultra Lotto 6/58"])

    def test_filters_results_by_game(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "pcso_results.json").write_text(json.dumps([
                {"lotto_game": "Lotto 6/42", "combinations": "01-02", "draw_date": "5/1/2026", "jackpot": "1", "winners": "0"},
                {"lotto_game": "Ultra Lotto 6/58", "combinations": "03-04", "draw_date": "5/2/2026", "jackpot": "2", "winners": "1"},
            ]), encoding="utf-8")

            rows = ResultsService(root).results_for_game("Ultra Lotto 6/58")

            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["combinations"], "03-04")

    def test_missing_results_file_raises_file_not_found(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(FileNotFoundError):
                ResultsService(Path(tmp)).list_results()
