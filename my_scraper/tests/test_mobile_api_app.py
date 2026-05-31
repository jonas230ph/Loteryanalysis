import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from mobile_api.app import create_app, runtime_config


class MobileAPITests(unittest.TestCase):
    def test_routes_return_mobile_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_fixture(root)
            app = create_app(root)

            results_status, results_body = app.handle_request("GET", "/api/results")
            games_status, games_body = app.handle_request("GET", "/api/games")
            game_status, game_body = app.handle_request("GET", "/api/games/Ultra%20Lotto%206%2F58/results")
            analysis_status, analysis_body = app.handle_request("GET", "/api/games/Ultra%20Lotto%206%2F58/analysis")
            suggestions_status, suggestions_body = app.handle_request("GET", "/api/suggestions")

            self.assertEqual(results_status, 200)
            self.assertEqual(json.loads(results_body)["results"][0]["lotto_game"], "Ultra Lotto 6/58")
            self.assertEqual(games_status, 200)
            self.assertEqual(json.loads(games_body)["games"], ["Ultra Lotto 6/58"])
            self.assertEqual(game_status, 200)
            self.assertEqual(json.loads(game_body)["results"][0]["combinations"], "01-02-03-04-05-06")
            self.assertEqual(analysis_status, 200)
            self.assertEqual(json.loads(analysis_body)["analysis"]["sum_statistics"]["count"], 1)
            self.assertEqual(suggestions_status, 200)
            self.assertEqual(len(json.loads(suggestions_body)["suggestions"]), 1)

    def test_unknown_route_returns_404(self):
        with tempfile.TemporaryDirectory() as tmp:
            status, body = create_app(Path(tmp)).handle_request("GET", "/missing")

            self.assertEqual(status, 404)
            self.assertEqual(json.loads(body)["error"], "Not found")

    def test_health_route_returns_ok(self):
        with tempfile.TemporaryDirectory() as tmp:
            status, body = create_app(Path(tmp)).handle_request("GET", "/api/health")

            self.assertEqual(status, 200)
            self.assertEqual(json.loads(body), {"status": "ok"})

    def test_runtime_config_uses_railway_port(self):
        with patch.dict(os.environ, {"HOST": "0.0.0.0", "PORT": "4321"}):
            self.assertEqual(runtime_config(), ("0.0.0.0", 4321))

    def _write_fixture(self, root):
        (root / "pcso_results.json").write_text(json.dumps([
            {
                "lotto_game": "Ultra Lotto 6/58",
                "combinations": "01-02-03-04-05-06",
                "draw_date": "5/3/2026",
                "jackpot": "50,000,000.00",
                "winners": "1",
            }
        ]), encoding="utf-8")
        outputs = root / "analysis_outputs"
        outputs.mkdir()
        (outputs / "number_frequency_by_game.csv").write_text("lotto_game,numbers,frequency\nUltra Lotto 6/58,1,12\n", encoding="utf-8")
        (outputs / "odd_even_patterns_by_game.csv").write_text("lotto_game,odd_even_pattern,draws\nUltra Lotto 6/58,3 odd / 3 even,1\n", encoding="utf-8")
        (outputs / "sum_statistics_by_game.csv").write_text("lotto_game,count,min,median,mean,max,std\nUltra Lotto 6/58,1,21,21,21,21,0\n", encoding="utf-8")
        (outputs / "possible_winning_numbers_by_game.csv").write_text(
            "lotto_game,suggested_combination,sum,odd_even_pattern,historical_frequency_score,basis\n"
            "Ultra Lotto 6/58,01-02-03-04-05-06,21,3 odd / 3 even,90,weighted\n",
            encoding="utf-8",
        )
