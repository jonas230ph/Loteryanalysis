import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class IOSAPIURLSourceTests(unittest.TestCase):
    def test_railway_api_url_does_not_include_internal_port(self):
        source = (PROJECT_ROOT / "ios_app/PCSOLotto/Services/APIClient.swift").read_text(encoding="utf-8")

        self.assertIn("https://loteryanalysis-production.up.railway.app", source)
        self.assertNotIn("up.railway.app:8080", source)
