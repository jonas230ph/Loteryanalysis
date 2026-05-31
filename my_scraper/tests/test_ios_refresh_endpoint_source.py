import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class IOSRefreshEndpointSourceTests(unittest.TestCase):
    def test_api_client_supports_post_requests(self):
        source = (PROJECT_ROOT / "ios_app/PCSOLotto/Services/APIClient.swift").read_text(encoding="utf-8")

        self.assertIn("func post<T: Decodable>", source)
        self.assertIn('request.httpMethod = "POST"', source)

    def test_repository_calls_refresh_endpoint(self):
        source = (PROJECT_ROOT / "ios_app/PCSOLotto/Services/LotteryRepository.swift").read_text(encoding="utf-8")

        self.assertIn("func refreshData() async throws", source)
        self.assertIn('client.post("api/refresh")', source)

    def test_view_model_refreshes_pipeline_before_loading_home(self):
        source = (PROJECT_ROOT / "ios_app/PCSOLotto/ViewModels/LotteryViewModel.swift").read_text(encoding="utf-8")

        self.assertIn("func refreshHome() async", source)
        self.assertIn("try await repository.refreshData()", source)
        self.assertIn("try await loadHomeData()", source)
