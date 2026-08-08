import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class IOSAPIURLSourceTests(unittest.TestCase):
    def test_koyeb_api_url_is_read_from_the_app_configuration(self):
        source = (PROJECT_ROOT / "ios_app/PCSOLotto/Services/APIClient.swift").read_text(encoding="utf-8")
        project = (PROJECT_ROOT / "ios_app/PCSOLotto/PCSOLotto.xcodeproj/project.pbxproj").read_text(encoding="utf-8")

        self.assertIn('object(forInfoDictionaryKey: "API_BASE_URL")', source)
        self.assertIn("INFOPLIST_KEY_API_BASE_URL", project)
        self.assertIn("REPLACE_WITH_YOUR_KOYEB_URL", project)
        self.assertNotIn("127.0.0.1", source)
        self.assertNotIn("up.railway.app", source)
