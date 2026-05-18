import json
import tempfile
import unittest
from pathlib import Path

from mobile_api.services.results_service import ResultsService
from mobile_api.services.analysis_service import AnalysisService


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


class AnalysisServiceTests(unittest.TestCase):
    def test_builds_game_analysis_from_csv_outputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            outputs = root / "analysis_outputs"
            outputs.mkdir()
            (outputs / "number_frequency_by_game.csv").write_text(
                "lotto_game,numbers,frequency\nUltra Lotto 6/58,1,12\nUltra Lotto 6/58,2,8\n",
                encoding="utf-8",
            )
            (outputs / "odd_even_patterns_by_game.csv").write_text(
                "lotto_game,odd_even_pattern,draws\nUltra Lotto 6/58,3 odd / 3 even,25\n",
                encoding="utf-8",
            )
            (outputs / "sum_statistics_by_game.csv").write_text(
                "lotto_game,count,min,median,mean,max,std\nUltra Lotto 6/58,30,80,150,151.5,220,20.4\n",
                encoding="utf-8",
            )

            analysis = AnalysisService(root).analysis_for_game("Ultra Lotto 6/58")

            self.assertEqual(analysis["lotto_game"], "Ultra Lotto 6/58")
            self.assertEqual(analysis["number_frequency"][0]["number"], 1)
            self.assertEqual(analysis["odd_even_patterns"][0]["pattern"], "3 odd / 3 even")
            self.assertEqual(analysis["sum_statistics"]["median"], 150.0)

    def test_lists_suggestions_from_csv(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            outputs = root / "analysis_outputs"
            outputs.mkdir()
            (outputs / "possible_winning_numbers_by_game.csv").write_text(
                "lotto_game,suggested_combination,sum,odd_even_pattern,historical_frequency_score,basis\n"
                "Ultra Lotto 6/58,01-02-03-04-05-06,21,3 odd / 3 even,90,weighted\n",
                encoding="utf-8",
            )

            suggestions = AnalysisService(root).list_suggestions()

            self.assertEqual(suggestions[0]["suggested_combination"], "01-02-03-04-05-06")
            self.assertEqual(suggestions[0]["historical_frequency_score"], 90)
