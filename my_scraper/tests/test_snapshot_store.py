import json
import unittest

from mobile_api.snapshot_store import SupabaseSnapshotStore


class _Response:
    def __init__(self, payload):
        self.payload = payload

    def read(self):
        return json.dumps(self.payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False


class SupabaseSnapshotStoreTests(unittest.TestCase):
    def test_loads_the_current_snapshot_payload_from_supabase(self):
        received = []

        def opener(request, timeout):
            received.append((request, timeout))
            return _Response([{
                "payload": {
                    "results": [{"lotto_game": "Ultra Lotto 6/58"}],
                    "games": ["Ultra Lotto 6/58"],
                    "suggestions": [],
                    "analysis_by_game": {},
                },
            }])

        store = SupabaseSnapshotStore(
            "https://project.supabase.co/",
            "publishable-key",
            opener=opener,
        )

        snapshot = store.load()

        self.assertEqual(snapshot["games"], ["Ultra Lotto 6/58"])
        self.assertEqual(
            received[0][0].full_url,
            "https://project.supabase.co/rest/v1/mobile_snapshots?id=eq.current&select=payload",
        )
        self.assertEqual(received[0][0].get_header("Authorization"), "Bearer publishable-key")
        self.assertEqual(received[0][1], 15)

    def test_publishes_the_current_snapshot_with_an_upsert(self):
        received = []

        def opener(request, timeout):
            received.append((request, timeout))
            return _Response([])

        store = SupabaseSnapshotStore(
            "https://project.supabase.co",
            "service-role-key",
            opener=opener,
        )
        store.publish({"results": [], "games": [], "suggestions": [], "analysis_by_game": {}})

        request = received[0][0]
        self.assertEqual(
            request.full_url,
            "https://project.supabase.co/rest/v1/mobile_snapshots?on_conflict=id",
        )
        self.assertEqual(request.get_method(), "POST")
        self.assertEqual(request.get_header("Prefer"), "resolution=merge-duplicates,return=minimal")
        self.assertEqual(json.loads(request.data)["id"], "current")
