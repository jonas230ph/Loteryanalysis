import hmac
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse
from urllib.request import Request, urlopen

from mobile_api.snapshot_store import (
    FileSnapshotStore,
    SnapshotUnavailableError,
    SupabaseSnapshotStore,
)


class MobileAPI:
    """Small HTTP API used by the iPhone app and its hosted deployment."""

    def __init__(self, project_root, snapshot_store=None):
        # Local development uses generated files. The hosted API reads the published
        # Supabase snapshot because a container filesystem is ephemeral.
        self.project_root = Path(project_root)
        self.snapshot_store = snapshot_store or build_snapshot_store(self.project_root)

    def handle_request(self, method, raw_path, headers=None):
        # The mobile app only needs read routes plus one refresh trigger route.
        if method not in {"GET", "HEAD", "POST"}:
            return self._json(405, {"error": "Method not allowed"})

        path = urlparse(raw_path).path
        try:
            if path == "/api/health":
                return self._json(200, {"status": "ok"})
            if method == "POST" and path == "/api/refresh":
                # Pull-to-refresh starts the GitHub workflow. It returns quickly
                # because this service is only the API, not the scraper worker.
                return self._refresh(headers or {})
            if method != "GET":
                return self._json(405, {"error": "Method not allowed"})
            if path not in {"/api/results", "/api/games", "/api/suggestions", "/api/ultra-lotto/trends"} and not path.startswith("/api/games/"):
                return self._json(404, {"error": "Not found"})
            snapshot = self.snapshot_store.load()
            if path == "/api/results":
                return self._json(200, {"results": snapshot["results"]})
            if path == "/api/games":
                return self._json(200, {"games": snapshot["games"]})
            if path == "/api/suggestions":
                return self._json(200, {"suggestions": snapshot["suggestions"]})
            if path == "/api/ultra-lotto/trends":
                # Older Supabase snapshots may not have this field until their
                # next scheduled pipeline run, so return an empty valid payload.
                return self._json(200, snapshot.get("ultra_lotto_trends", empty_ultra_lotto_trends()))
            if path.startswith("/api/games/"):
                return self._handle_game_route(path, snapshot)
            return self._json(404, {"error": "Not found"})
        except FileNotFoundError as exc:
            return self._json(503, {"error": str(exc)})
        except SnapshotUnavailableError as exc:
            return self._json(503, {"error": str(exc)})
        except ValueError as exc:
            return self._json(400, {"error": str(exc)})

    def _handle_game_route(self, path, snapshot):
        # Game names are URL-encoded in Swift, so decode them before matching
        # against the lottery names stored in the JSON/CSV output files.
        suffixes = {
            "/results": lambda game: {
                "results": [
                    row for row in snapshot["results"]
                    if row["lotto_game"] == game
                ],
            },
            "/analysis": lambda game: {
                "analysis": snapshot["analysis_by_game"].get(game, empty_analysis(game)),
            },
        }
        for suffix, loader in suffixes.items():
            if path.endswith(suffix):
                encoded_game = path[len("/api/games/"):-len(suffix)]
                game = unquote(encoded_game)
                return self._json(200, loader(game))
        return self._json(404, {"error": "Not found"})

    def _json(self, status, payload):
        # Keep response creation in one place so every route returns valid JSON.
        return status, json.dumps(payload, ensure_ascii=False)

    def _refresh(self, headers):
        # GitHub Actions has a durable workspace for the Python pipeline. A
        # fine-grained token is held only in the host's secret configuration.
        token = os.getenv("GITHUB_REFRESH_TOKEN")
        repository = os.getenv("GITHUB_REPOSITORY")
        workflow = os.getenv("GITHUB_REFRESH_WORKFLOW", "refresh-lottery-data.yml")
        ref = os.getenv("GITHUB_REFRESH_REF", "main")
        if not token or not repository:
            return self._json(503, {"error": "Remote refresh is not configured"})
        expected_key = os.getenv("REFRESH_REQUEST_KEY")
        supplied_key = next(
            (value for name, value in headers.items() if name.lower() == "x-pcso-refresh-key"),
            "",
        )
        if not expected_key or not hmac.compare_digest(supplied_key, expected_key):
            return self._json(401, {"error": "Refresh request is not authorized"})

        request = Request(
            f"https://api.github.com/repos/{repository}/actions/workflows/{workflow}/dispatches",
            data=json.dumps({"ref": ref}).encode("utf-8"),
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
            method="POST",
        )
        try:
            with urlopen(request, timeout=15):
                return self._json(202, {
                    "status": "refresh_started",
                    "message": "The latest draw data will be available in a few minutes.",
                })
        except Exception:
            return self._json(502, {"error": "Unable to start the remote refresh"})


def create_app(project_root=None):
    # Tests can inject a temporary project root; production uses the repo root.
    return MobileAPI(project_root or Path(__file__).resolve().parents[1])


def build_snapshot_store(project_root):
    # Render receives these values as environment variables. Missing values
    # intentionally select files so local API commands need no cloud setup.
    project_url = os.getenv("SUPABASE_URL")
    publishable_key = os.getenv("SUPABASE_PUBLISHABLE_KEY")
    if project_url and publishable_key:
        return SupabaseSnapshotStore(project_url, publishable_key)
    return FileSnapshotStore(project_root)


def empty_analysis(game):
    # New games can be present in results before their analysis has data.
    return {
        "lotto_game": game,
        "number_frequency": [],
        "odd_even_patterns": [],
        "sum_statistics": None,
    }


def empty_ultra_lotto_trends():
    """Empty shape lets new app versions read an older published snapshot."""
    return {"odd_even_patterns": [], "suggestions": []}


def runtime_config():
    # Render supplies PORT at runtime. HOST defaults to all interfaces for containers.
    return os.getenv("HOST", "0.0.0.0"), int(os.getenv("PORT", "8080"))


def run(host=None, port=None, project_root=None):
    default_host, default_port = runtime_config()
    host = host or default_host
    port = port or default_port
    app = create_app(project_root)

    class Handler(BaseHTTPRequestHandler):
        # BaseHTTPRequestHandler maps HTTP verbs to these do_* methods.
        def do_GET(self):
            status, body = app.handle_request("GET", self.path)
            self._send_json(status, body, include_body=True)

        def do_HEAD(self):
            status, body = app.handle_request("HEAD", self.path)
            self._send_json(status, body, include_body=False)

        def do_POST(self):
            status, body = app.handle_request("POST", self.path, dict(self.headers.items()))
            self._send_json(status, body, include_body=True)

        def _send_json(self, status, body, include_body):
            # HEAD responses include headers only, so callers can health-check
            # the service without downloading a response body.
            encoded = body.encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(encoded)))
            self.end_headers()
            if include_body:
                self.wfile.write(encoded)

        def log_message(self, format, *args):
            # Silence default request logging so Render logs focus on pipeline
            # output and real errors.
            return

    server = ThreadingHTTPServer((host, port), Handler)
    print(f"Serving PCSO mobile API at http://{host}:{port}")
    server.serve_forever()


if __name__ == "__main__":
    run()
