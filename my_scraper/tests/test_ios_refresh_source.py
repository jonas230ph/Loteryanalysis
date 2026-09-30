import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class IOSRefreshSourceTests(unittest.TestCase):
    def test_results_view_has_pull_to_refresh_and_toolbar_refresh_button(self):
        source = (PROJECT_ROOT / "ios_app/PCSOLotto/Views/ResultsView.swift").read_text(encoding="utf-8")

        self.assertIn(".refreshable", source)
        self.assertIn("ToolbarItem", source)
        self.assertIn('Image(systemName: "arrow.clockwise")', source)
        self.assertIn("await viewModel.refreshHome()", source)

    def test_suggestions_view_has_pull_to_refresh_and_toolbar_refresh_button(self):
        source = (PROJECT_ROOT / "ios_app/PCSOLotto/Views/SuggestionsView.swift").read_text(encoding="utf-8")

        self.assertIn(".refreshable", source)
        self.assertIn("ToolbarItem", source)
        self.assertIn('Image(systemName: "arrow.clockwise")', source)
        self.assertIn("await viewModel.refreshHome()", source)

    def test_ultra_trends_tab_shows_the_moving_odd_even_basis(self):
        app_source = (PROJECT_ROOT / "ios_app/PCSOLotto/PCSOLottoApp.swift").read_text(encoding="utf-8")
        view_source = (PROJECT_ROOT / "ios_app/PCSOLotto/Views/SuggestionsView.swift").read_text(encoding="utf-8")

        self.assertIn("UltraTrendsView", app_source)
        self.assertIn('Label("Ultra Trends", systemImage: "chart.bar.xaxis")', app_source)
        self.assertIn("Moving Four-Week Odd / Even Basis", view_source)
        self.assertIn("await viewModel.refreshHome()", view_source)

    def test_ultra_trends_tab_checks_six_entered_numbers_against_latest_draw(self):
        source = (PROJECT_ROOT / "ios_app/PCSOLotto/Views/SuggestionsView.swift").read_text(encoding="utf-8")

        self.assertIn("Check Latest Ultra Lotto Draw", source)
        self.assertIn("Enter 6 numbers", source)
        self.assertIn("latestUltraResult", source)
        self.assertIn("Set(submittedNumbers)", source)
        self.assertIn("Matched", source)
        self.assertIn('enteredNumbers = ["", "", ""]', source)
        self.assertIn('Button("Check Set', source)
        self.assertIn('Text(matchedText).bold().foregroundStyle(.red)', source)
        self.assertIn('@AppStorage("ultraLottoCheckerEntries")', source)
        self.assertIn("restoreEnteredNumbers()", source)
        self.assertIn("clearChecker(at: slot)", source)
        self.assertIn("clearAllCheckers()", source)
