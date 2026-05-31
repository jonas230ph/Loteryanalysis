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
