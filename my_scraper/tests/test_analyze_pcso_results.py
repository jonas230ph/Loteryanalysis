import unittest

import pandas as pd

from analyze_pcso_results import (
    daily_odd_even_analysis,
    frequency_analysis,
    suggest_combinations,
    sum_analysis,
    ultra_lotto_trend_analysis,
    ultra_lotto_trend_suggestions,
)


class DailyOddEvenAnalysisTests(unittest.TestCase):
    def test_aggregates_odd_and_even_numbers_by_game_and_draw_date(self):
        draws = pd.DataFrame({
            "draw_date": pd.to_datetime(["2026-08-08", "2026-08-08", "2026-08-09"]),
            "lotto_game": ["Lotto 6/42", "Lotto 6/42", "Ultra Lotto 6/58"],
            "odd_count": [2, 3, 4],
            "even_count": [2, 0, 2],
        })

        report = daily_odd_even_analysis(draws)

        lotto_row = report.iloc[1]
        self.assertEqual(lotto_row["draw_date"], "2026-08-08")
        self.assertEqual(lotto_row["lotto_game"], "Lotto 6/42")
        self.assertEqual(lotto_row["draws"], 2)
        self.assertEqual(lotto_row["odd_numbers"], 5)
        self.assertEqual(lotto_row["even_numbers"], 2)
        self.assertEqual(lotto_row["total_numbers"], 7)
        self.assertEqual(lotto_row["odd_percentage"], 71.43)
        self.assertEqual(lotto_row["even_percentage"], 28.57)


class SuggestionOddEvenTests(unittest.TestCase):
    def test_uses_each_games_latest_six_weeks_of_odd_even_numbers_and_lists_ultra_first(self):
        draws = pd.DataFrame({
            "draw_date": pd.to_datetime([
                "2026-08-01", "2026-09-01", "2026-09-15", "2026-10-01",
                "2026-09-01", "2026-09-15", "2026-10-01",
            ]),
            "lotto_game": ["Ultra Lotto 6/58"] * 4 + ["Lotto 6/42"] * 3,
            "numbers": [[1, 3, 5, 2, 4, 6]] + [[1, 3, 5, 7, 2, 4]] * 6,
            "odd_count": [3, 4, 4, 4, 4, 4, 4],
            "even_count": [3, 2, 2, 2, 2, 2, 2],
            "sum": [21, 22, 22, 22, 22, 22, 22],
        })

        suggestions = suggest_combinations(
            draws,
            frequency_analysis(draws),
            sum_analysis(draws),
            suggestions_per_game=1,
            seed=7,
        )

        self.assertEqual(suggestions.iloc[0]["lotto_game"], "Ultra Lotto 6/58")
        self.assertTrue((suggestions["odd_even_pattern"] == "4 odd / 2 even").all())
        self.assertIn("six-week odd/even number frequency", suggestions.iloc[0]["basis"])

    def test_adds_two_alternate_odd_even_mixes_to_five_ultra_lotto_suggestions(self):
        draws = pd.DataFrame({
            "draw_date": pd.to_datetime(["2026-09-30"] * 6 + ["2026-10-01"] * 6),
            "lotto_game": ["Ultra Lotto 6/58"] * 12,
            "numbers": [[1, 3, 5, 7, 9, 11]] * 6 + [[2, 4, 6, 8, 10, 12]] * 6,
            "odd_count": [6] * 6 + [0] * 6,
            "even_count": [0] * 6 + [6] * 6,
            "sum": [0] * 6 + [100] * 6,
        })

        suggestions = suggest_combinations(
            draws,
            frequency_analysis(draws),
            sum_analysis(draws),
            suggestions_per_game=5,
            seed=7,
        )

        self.assertEqual(len(suggestions), 5)
        alternate_suggestions = suggestions[suggestions["basis"].str.contains("randomized odd/even")]
        self.assertEqual(len(alternate_suggestions), 2)
        self.assertSetEqual(
            set(alternate_suggestions["odd_even_pattern"]),
            {"4 odd / 2 even", "5 odd / 1 even"},
        )


class UltraLottoTrendAnalysisTests(unittest.TestCase):
    def test_ranks_recent_number_trends_and_generates_pattern_matched_combinations(self):
        draws = pd.DataFrame({
            "draw_date": pd.to_datetime([
                "2026-08-09", "2026-08-07", "2026-08-05", "2026-08-03", "2026-07-30",
            ]),
            "lotto_game": ["Ultra Lotto 6/58"] * 5,
            "numbers": [
                [1, 3, 5, 7, 10, 12],
                [1, 3, 5, 7, 10, 12],
                [1, 3, 5, 7, 10, 12],
                [1, 3, 5, 7, 10, 12],
                [2, 4, 6, 8, 9, 11],
            ],
            "odd_count": [4, 4, 4, 4, 2],
            "even_count": [2, 2, 2, 2, 4],
            "sum": [38, 38, 38, 38, 40],
        })

        trends, patterns, recent_draws = ultra_lotto_trend_analysis(draws, recent_window=4)
        suggestions = ultra_lotto_trend_suggestions(
            recent_draws,
            trends,
            patterns,
            suggestion_count=1,
            seed=7,
        )

        number_one = trends.loc[trends["number"] == 1].iloc[0]
        self.assertEqual(number_one["recent_frequency"], 4)
        self.assertEqual(number_one["historical_frequency"], 4)
        self.assertEqual(number_one["trend_delta_percentage_points"], 20.0)
        self.assertEqual(patterns.iloc[0]["odd_even_pattern"], "4 odd / 2 even")
        self.assertEqual(patterns.iloc[0]["draws"], 4)
        self.assertEqual(len(suggestions), 1)
        self.assertEqual(suggestions.iloc[0]["odd_count"], 4)
        self.assertEqual(suggestions.iloc[0]["even_count"], 2)
        self.assertIn("historical analysis", suggestions.iloc[0]["basis"])

    def test_uses_only_the_latest_four_calendar_weeks_for_odd_even_patterns(self):
        draws = pd.DataFrame({
            "draw_date": pd.to_datetime([
                "2026-08-09", "2026-08-05", "2026-08-01", "2026-07-28", "2026-07-10", "2026-07-08",
            ]),
            "lotto_game": ["Ultra Lotto 6/58"] * 6,
            "numbers": [[1, 3, 5, 7, 10, 12]] * 4 + [[1, 3, 5, 7, 9, 11]] * 2,
            "odd_count": [4, 4, 4, 4, 6, 6],
            "even_count": [2, 2, 2, 2, 0, 0],
            "sum": [38, 38, 38, 38, 36, 36],
        })

        _, patterns, _ = ultra_lotto_trend_analysis(draws, recent_window=6, odd_even_weeks=4)

        self.assertEqual(patterns.iloc[0]["odd_even_pattern"], "4 odd / 2 even")
        self.assertEqual(patterns.iloc[0]["draws"], 4)
        self.assertEqual(patterns.iloc[0]["moving_window_days"], 28)
        self.assertEqual(patterns.iloc[0]["moving_window_start"], "2026-07-13")
        self.assertEqual(patterns.iloc[0]["moving_window_end"], "2026-08-09")
        self.assertEqual(patterns.iloc[0]["moving_window_draws"], 4)
