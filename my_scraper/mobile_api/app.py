import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse

from mobile_api.services.analysis_service import AnalysisService
from mobile_api.services.results_service import ResultsService


class MobileAPI:
    def __init__(self, project_root):
        self.project_root = Path(project_root)
        self.results_service = ResultsService(self.project_root)
        self.analysis_service = AnalysisService(self.project_root)

    def handle_request(self, method, raw_path):
        if method != "GET":
            return self._json(405, {"error": "Method not allowed"})

        path = urlparse(raw_path).path
        try:
            if path == "/api/results":
                return self._json(200, {"results": self.results_service.list_results()})
            if path == "/api/games":
                return self._json(200, {"games": self.results_service.list_games()})
            if path == "/api/suggestions":
                return self._json(200, {"suggestions": self.analysis_service.list_suggestions()})
            if path.startswith("/api/games/"):
                return self._handle_game_route(path)
            return self._json(404, {"error": "Not found"})
        except FileNotFoundError as exc:
            return self._json(503, {"error": str(exc)})
        except ValueError as exc:
            return self._json(400, {"error": str(exc)})

    def _handle_game_route(self, path):
        suffixes = {
            "/results": lambda game: {"results": self.results_service.results_for_game(game)},
            "/analysis": lambda game: {"analysis": self.analysis_service.analysis_for_game(game)},
        }
        for suffix, loader in suffixes.items():
            if path.endswith(suffix):
                encoded_game = path[len("/api/games/"):-len(suffix)]
                game = unquote(encoded_game)
                return self._json(200, loader(game))
        return self._json(404, {"error": "Not found"})

    def _json(self, status, payload):
        return status, json.dumps(payload, ensure_ascii=False)


def create_app(project_root=None):
    return MobileAPI(project_root or Path(__file__).resolve().parents[1])


def run(host="127.0.0.1", port=8080, project_root=None):
    app = create_app(project_root)

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            status, body = app.handle_request("GET", self.path)
            encoded = body.encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(encoded)))
            self.end_headers()
            self.wfile.write(encoded)

        def log_message(self, format, *args):
            return

    server = ThreadingHTTPServer((host, port), Handler)
    print(f"Serving PCSO mobile API at http://{host}:{port}")
    server.serve_forever()


if __name__ == "__main__":
    run()
