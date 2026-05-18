# PCSO iOS Mobile App Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a native SwiftUI PCSO companion app backed by a small local Python JSON API that serves lottery results, game analysis, and generated suggestions.

**Architecture:** Keep scraping and analysis in Python. Add a dependency-light `mobile_api/` module that reads `pcso_results.json` and `analysis_outputs/*.csv`, then serves mobile-shaped JSON over HTTP. Add a SwiftUI source tree under `ios_app/PCSOLotto/` with models, services, repositories, view models, and views that consume the API.

**Tech Stack:** Python standard library HTTP server, `unittest`, Swift 5, SwiftUI, Foundation networking, XCTest-compatible model/service code.

---

## File Structure

- Create `mobile_api/__init__.py`: package marker.
- Create `mobile_api/services/__init__.py`: service package marker.
- Create `mobile_api/services/results_service.py`: load, normalize, sort, and filter `pcso_results.json`.
- Create `mobile_api/services/analysis_service.py`: load analysis CSV files and shape per-game summaries and suggestions.
- Create `mobile_api/app.py`: standard-library HTTP API with `/api/results`, `/api/games`, `/api/games/{game}/results`, `/api/games/{game}/analysis`, and `/api/suggestions`.
- Create `tests/test_mobile_api_services.py`: service-level tests using temporary JSON/CSV fixtures.
- Create `tests/test_mobile_api_app.py`: endpoint tests against the request handler without starting a long-lived server.
- Create `tests/__init__.py`: test package marker for `python -m unittest tests...` commands.
- Create `ios_app/PCSOLotto/Models/LottoResult.swift`: Swift result model.
- Create `ios_app/PCSOLotto/Models/GameAnalysis.swift`: Swift analysis models.
- Create `ios_app/PCSOLotto/Models/Suggestion.swift`: Swift suggestion model.
- Create `ios_app/PCSOLotto/Services/APIClient.swift`: configurable HTTP client and JSON decoder.
- Create `ios_app/PCSOLotto/Services/LotteryRepository.swift`: app-facing data access.
- Create `ios_app/PCSOLotto/ViewModels/LotteryViewModel.swift`: observable loading/error/data state.
- Create `ios_app/PCSOLotto/Views/ResultsView.swift`: searchable results list.
- Create `ios_app/PCSOLotto/Views/GameDetailView.swift`: selected game history and analysis navigation.
- Create `ios_app/PCSOLotto/Views/AnalysisView.swift`: frequency, pattern, and sum-stat display.
- Create `ios_app/PCSOLotto/Views/SuggestionsView.swift`: generated suggestions plus disclaimer.
- Create `ios_app/PCSOLotto/PCSOLottoApp.swift`: SwiftUI app entry point.
- Create `ios_app/PCSOLotto/README.md`: explains how to add the SwiftUI files to an Xcode iOS App target and configure the API base URL.

## Task 1: Backend Result Service

**Files:**
- Create: `mobile_api/__init__.py`
- Create: `mobile_api/services/__init__.py`
- Create: `mobile_api/services/results_service.py`
- Create: `tests/__init__.py`
- Test: `tests/test_mobile_api_services.py`

- [ ] **Step 1: Write failing service tests**

Add this file:

```python
import json
import tempfile
import unittest
from pathlib import Path

from mobile_api.services.results_service import ResultsService


class ResultsServiceTests(unittest.TestCase):
    def test_loads_results_sorted_newest_first_and_lists_games(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "pcso_results.json").write_text(json.dumps([
                {
                    "lotto_game": "Lotto 6/42",
                    "combinations": "01-02-03-04-05-06",
                    "draw_date": "5/1/2026",
                    "jackpot": "10,000,000.00",
                    "winners": "0",
                },
                {
                    "lotto_game": "Ultra Lotto 6/58",
                    "combinations": "10-11-12-13-14-15",
                    "draw_date": "5/3/2026",
                    "jackpot": "50,000,000.00",
                    "winners": "1",
                },
            ]), encoding="utf-8")

            service = ResultsService(root)

            self.assertEqual(
                [row["lotto_game"] for row in service.list_results()],
                ["Ultra Lotto 6/58", "Lotto 6/42"],
            )
            self.assertEqual(service.list_games(), ["Lotto 6/42", "Ultra Lotto 6/58"])

    def test_filters_results_by_game(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "pcso_results.json").write_text(json.dumps([
                {"lotto_game": "Lotto 6/42", "combinations": "01-02", "draw_date": "5/1/2026", "jackpot": "1", "winners": "0"},
                {"lotto_game": "Ultra Lotto 6/58", "combinations": "03-04", "draw_date": "5/2/2026", "jackpot": "2", "winners": "1"},
            ]), encoding="utf-8")

            rows = ResultsService(root).results_for_game("Ultra Lotto 6/58")

            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["combinations"], "03-04")

    def test_missing_results_file_raises_file_not_found(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(FileNotFoundError):
                ResultsService(Path(tmp)).list_results()
```

- [ ] **Step 2: Run tests to verify failure**

Run: `./pcso_env/bin/python -m unittest tests.test_mobile_api_services -v`

Expected: FAIL with `ModuleNotFoundError: No module named 'mobile_api'`.

- [ ] **Step 3: Implement result service**

Create empty package files:

```python
# mobile_api/__init__.py
```

```python
# mobile_api/services/__init__.py
```

```python
# tests/__init__.py
```

Create `mobile_api/services/results_service.py`:

```python
import json
from datetime import datetime
from pathlib import Path


def _parse_draw_date(value):
    parsed = datetime.strptime(value, "%m/%d/%Y")
    return parsed.date().isoformat()


class ResultsService:
    def __init__(self, project_root):
        self.project_root = Path(project_root)
        self.results_path = self.project_root / "pcso_results.json"

    def list_results(self):
        if not self.results_path.exists():
            raise FileNotFoundError(f"Missing results file: {self.results_path}")

        records = json.loads(self.results_path.read_text(encoding="utf-8"))
        normalized = [self._normalize_record(record) for record in records]
        return sorted(normalized, key=lambda row: row["draw_date"], reverse=True)

    def list_games(self):
        return sorted({row["lotto_game"] for row in self.list_results()})

    def results_for_game(self, game):
        return [row for row in self.list_results() if row["lotto_game"] == game]

    def _normalize_record(self, record):
        return {
            "lotto_game": str(record.get("lotto_game", "")).strip(),
            "combinations": str(record.get("combinations", "")).strip(),
            "draw_date": _parse_draw_date(str(record.get("draw_date", "")).strip()),
            "jackpot": str(record.get("jackpot", "")).strip(),
            "winners": str(record.get("winners", "")).strip(),
        }
```

- [ ] **Step 4: Run service tests**

Run: `./pcso_env/bin/python -m unittest tests.test_mobile_api_services -v`

Expected: PASS for all `ResultsServiceTests`.

- [ ] **Step 5: Commit**

```bash
git add mobile_api tests/test_mobile_api_services.py
git commit -m "Add mobile API result service"
```

## Task 2: Backend Analysis Service

**Files:**
- Create: `mobile_api/services/analysis_service.py`
- Modify: `tests/test_mobile_api_services.py`

- [ ] **Step 1: Add failing analysis tests**

Append to `tests/test_mobile_api_services.py`:

```python
from mobile_api.services.analysis_service import AnalysisService


class AnalysisServiceTests(unittest.TestCase):
    def test_builds_game_analysis_from_csv_outputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            outputs = root / "analysis_outputs"
            outputs.mkdir()
            (outputs / "number_frequency_by_game.csv").write_text(
                "lotto_game,numbers,frequency\nUltra Lotto 6/58,1,12\nUltra Lotto 6/58,2,8\n",
                encoding="utf-8",
            )
            (outputs / "odd_even_patterns_by_game.csv").write_text(
                "lotto_game,odd_even_pattern,draws\nUltra Lotto 6/58,3 odd / 3 even,25\n",
                encoding="utf-8",
            )
            (outputs / "sum_statistics_by_game.csv").write_text(
                "lotto_game,count,min,median,mean,max,std\nUltra Lotto 6/58,30,80,150,151.5,220,20.4\n",
                encoding="utf-8",
            )

            analysis = AnalysisService(root).analysis_for_game("Ultra Lotto 6/58")

            self.assertEqual(analysis["lotto_game"], "Ultra Lotto 6/58")
            self.assertEqual(analysis["number_frequency"][0]["number"], 1)
            self.assertEqual(analysis["odd_even_patterns"][0]["pattern"], "3 odd / 3 even")
            self.assertEqual(analysis["sum_statistics"]["median"], 150.0)

    def test_lists_suggestions_from_csv(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            outputs = root / "analysis_outputs"
            outputs.mkdir()
            (outputs / "possible_winning_numbers_by_game.csv").write_text(
                "lotto_game,suggested_combination,sum,odd_even_pattern,historical_frequency_score,basis\n"
                "Ultra Lotto 6/58,01-02-03-04-05-06,21,3 odd / 3 even,90,weighted\n",
                encoding="utf-8",
            )

            suggestions = AnalysisService(root).list_suggestions()

            self.assertEqual(suggestions[0]["suggested_combination"], "01-02-03-04-05-06")
            self.assertEqual(suggestions[0]["historical_frequency_score"], 90)
```

- [ ] **Step 2: Run tests to verify failure**

Run: `./pcso_env/bin/python -m unittest tests.test_mobile_api_services -v`

Expected: FAIL with `ModuleNotFoundError: No module named 'mobile_api.services.analysis_service'`.

- [ ] **Step 3: Implement analysis service**

Create `mobile_api/services/analysis_service.py`:

```python
import csv
from pathlib import Path


class AnalysisService:
    def __init__(self, project_root):
        self.project_root = Path(project_root)
        self.output_dir = self.project_root / "analysis_outputs"

    def analysis_for_game(self, game):
        frequency = [
            {
                "number": int(row["numbers"]),
                "frequency": int(row["frequency"]),
            }
            for row in self._read_csv("number_frequency_by_game.csv")
            if row["lotto_game"] == game
        ]
        patterns = [
            {
                "pattern": row["odd_even_pattern"],
                "draws": int(row["draws"]),
            }
            for row in self._read_csv("odd_even_patterns_by_game.csv")
            if row["lotto_game"] == game
        ]
        sum_rows = [
            row for row in self._read_csv("sum_statistics_by_game.csv")
            if row["lotto_game"] == game
        ]

        if not frequency and not patterns and not sum_rows:
            return {
                "lotto_game": game,
                "number_frequency": [],
                "odd_even_patterns": [],
                "sum_statistics": None,
            }

        return {
            "lotto_game": game,
            "number_frequency": frequency,
            "odd_even_patterns": patterns,
            "sum_statistics": self._normalize_sum_stats(sum_rows[0]) if sum_rows else None,
        }

    def list_suggestions(self):
        return [
            {
                "lotto_game": row["lotto_game"],
                "suggested_combination": row["suggested_combination"],
                "sum": int(float(row["sum"])),
                "odd_even_pattern": row["odd_even_pattern"],
                "historical_frequency_score": int(float(row["historical_frequency_score"])),
                "basis": row["basis"],
            }
            for row in self._read_csv("possible_winning_numbers_by_game.csv")
        ]

    def _read_csv(self, filename):
        path = self.output_dir / filename
        if not path.exists():
            raise FileNotFoundError(f"Missing analysis file: {path}")
        with path.open(newline="", encoding="utf-8") as file:
            return list(csv.DictReader(file))

    def _normalize_sum_stats(self, row):
        return {
            "count": int(float(row["count"])),
            "min": float(row["min"]),
            "median": float(row["median"]),
            "mean": float(row["mean"]),
            "max": float(row["max"]),
            "std": float(row["std"]),
        }
```

- [ ] **Step 4: Run service tests**

Run: `./pcso_env/bin/python -m unittest tests.test_mobile_api_services -v`

Expected: PASS for all service tests.

- [ ] **Step 5: Commit**

```bash
git add mobile_api/services/analysis_service.py tests/test_mobile_api_services.py
git commit -m "Add mobile API analysis service"
```

## Task 3: Mobile API HTTP Endpoints

**Files:**
- Create: `mobile_api/app.py`
- Create: `tests/test_mobile_api_app.py`

- [ ] **Step 1: Write failing endpoint tests**

Create `tests/test_mobile_api_app.py`:

```python
import json
import tempfile
import unittest
from pathlib import Path

from mobile_api.app import create_app


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
```

- [ ] **Step 2: Run endpoint tests to verify failure**

Run: `./pcso_env/bin/python -m unittest tests.test_mobile_api_app -v`

Expected: FAIL with `ModuleNotFoundError: No module named 'mobile_api.app'`.

- [ ] **Step 3: Implement mobile API app**

Create `mobile_api/app.py`:

```python
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
```

- [ ] **Step 4: Run all backend tests**

Run: `./pcso_env/bin/python -m unittest tests.test_mobile_api_services tests.test_mobile_api_app -v`

Expected: PASS.

- [ ] **Step 5: Smoke test the local API**

Run in one terminal: `./pcso_env/bin/python -m mobile_api.app`

Run in another terminal: `curl http://127.0.0.1:8080/api/games`

Expected: JSON with a `games` array.

- [ ] **Step 6: Commit**

```bash
git add mobile_api tests
git commit -m "Add mobile JSON API"
```

## Task 4: Swift Models and API Client

**Files:**
- Create: `ios_app/PCSOLotto/Models/LottoResult.swift`
- Create: `ios_app/PCSOLotto/Models/GameAnalysis.swift`
- Create: `ios_app/PCSOLotto/Models/Suggestion.swift`
- Create: `ios_app/PCSOLotto/Services/APIClient.swift`
- Create: `ios_app/PCSOLotto/Services/LotteryRepository.swift`

- [ ] **Step 1: Create Swift models**

Create `ios_app/PCSOLotto/Models/LottoResult.swift`:

```swift
import Foundation

struct LottoResult: Identifiable, Codable, Hashable {
    var id: String { "\(lottoGame)-\(drawDate)-\(combinations)" }
    let lottoGame: String
    let combinations: String
    let drawDate: String
    let jackpot: String
    let winners: String

    enum CodingKeys: String, CodingKey {
        case lottoGame = "lotto_game"
        case combinations
        case drawDate = "draw_date"
        case jackpot
        case winners
    }
}

struct ResultsResponse: Codable {
    let results: [LottoResult]
}

struct GamesResponse: Codable {
    let games: [String]
}
```

Create `ios_app/PCSOLotto/Models/GameAnalysis.swift`:

```swift
import Foundation

struct GameAnalysis: Codable, Hashable {
    let lottoGame: String
    let numberFrequency: [NumberFrequency]
    let oddEvenPatterns: [OddEvenPattern]
    let sumStatistics: SumStatistics?

    enum CodingKeys: String, CodingKey {
        case lottoGame = "lotto_game"
        case numberFrequency = "number_frequency"
        case oddEvenPatterns = "odd_even_patterns"
        case sumStatistics = "sum_statistics"
    }
}

struct NumberFrequency: Identifiable, Codable, Hashable {
    var id: Int { number }
    let number: Int
    let frequency: Int
}

struct OddEvenPattern: Identifiable, Codable, Hashable {
    var id: String { pattern }
    let pattern: String
    let draws: Int
}

struct SumStatistics: Codable, Hashable {
    let count: Int
    let min: Double
    let median: Double
    let mean: Double
    let max: Double
    let std: Double
}

struct AnalysisResponse: Codable {
    let analysis: GameAnalysis
}
```

Create `ios_app/PCSOLotto/Models/Suggestion.swift`:

```swift
import Foundation

struct Suggestion: Identifiable, Codable, Hashable {
    var id: String { "\(lottoGame)-\(suggestedCombination)" }
    let lottoGame: String
    let suggestedCombination: String
    let sum: Int
    let oddEvenPattern: String
    let historicalFrequencyScore: Int
    let basis: String

    enum CodingKeys: String, CodingKey {
        case lottoGame = "lotto_game"
        case suggestedCombination = "suggested_combination"
        case sum
        case oddEvenPattern = "odd_even_pattern"
        case historicalFrequencyScore = "historical_frequency_score"
        case basis
    }
}

struct SuggestionsResponse: Codable {
    let suggestions: [Suggestion]
}
```

- [ ] **Step 2: Create API client and repository**

Create `ios_app/PCSOLotto/Services/APIClient.swift`:

```swift
import Foundation

enum APIClientError: Error, LocalizedError {
    case invalidResponse
    case serverMessage(String)

    var errorDescription: String? {
        switch self {
        case .invalidResponse:
            return "The server returned an invalid response."
        case .serverMessage(let message):
            return message
        }
    }
}

struct APIErrorResponse: Codable {
    let error: String
}

final class APIClient {
    let baseURL: URL
    private let session: URLSession
    private let decoder: JSONDecoder

    init(baseURL: URL = URL(string: "http://127.0.0.1:8080")!, session: URLSession = .shared) {
        if baseURL.absoluteString.hasSuffix("/") {
            self.baseURL = baseURL
        } else {
            self.baseURL = URL(string: baseURL.absoluteString + "/")!
        }
        self.session = session
        self.decoder = JSONDecoder()
    }

    func get<T: Decodable>(_ path: String) async throws -> T {
        guard let url = URL(string: path, relativeTo: baseURL)?.absoluteURL else {
            throw APIClientError.invalidResponse
        }
        let (data, response) = try await session.data(from: url)
        guard let httpResponse = response as? HTTPURLResponse else {
            throw APIClientError.invalidResponse
        }
        guard (200..<300).contains(httpResponse.statusCode) else {
            let apiError = try? decoder.decode(APIErrorResponse.self, from: data)
            throw APIClientError.serverMessage(apiError?.error ?? "Request failed.")
        }
        return try decoder.decode(T.self, from: data)
    }
}
```

Create `ios_app/PCSOLotto/Services/LotteryRepository.swift`:

```swift
import Foundation

final class LotteryRepository {
    private let client: APIClient

    init(client: APIClient = APIClient()) {
        self.client = client
    }

    func fetchResults() async throws -> [LottoResult] {
        let response: ResultsResponse = try await client.get("api/results")
        return response.results
    }

    func fetchGames() async throws -> [String] {
        let response: GamesResponse = try await client.get("api/games")
        return response.games
    }

    func fetchResults(for game: String) async throws -> [LottoResult] {
        var allowed = CharacterSet.urlPathAllowed
        allowed.remove(charactersIn: "/")
        let encoded = game.addingPercentEncoding(withAllowedCharacters: allowed) ?? game
        let response: ResultsResponse = try await client.get("api/games/\(encoded)/results")
        return response.results
    }

    func fetchAnalysis(for game: String) async throws -> GameAnalysis {
        var allowed = CharacterSet.urlPathAllowed
        allowed.remove(charactersIn: "/")
        let encoded = game.addingPercentEncoding(withAllowedCharacters: allowed) ?? game
        let response: AnalysisResponse = try await client.get("api/games/\(encoded)/analysis")
        return response.analysis
    }

    func fetchSuggestions() async throws -> [Suggestion] {
        let response: SuggestionsResponse = try await client.get("api/suggestions")
        return response.suggestions
    }
}
```

- [ ] **Step 3: Commit**

```bash
git add ios_app/PCSOLotto/Models ios_app/PCSOLotto/Services
git commit -m "Add Swift mobile models and API client"
```

## Task 5: SwiftUI View Models and Screens

**Files:**
- Create: `ios_app/PCSOLotto/ViewModels/LotteryViewModel.swift`
- Create: `ios_app/PCSOLotto/Views/ResultsView.swift`
- Create: `ios_app/PCSOLotto/Views/GameDetailView.swift`
- Create: `ios_app/PCSOLotto/Views/AnalysisView.swift`
- Create: `ios_app/PCSOLotto/Views/SuggestionsView.swift`
- Create: `ios_app/PCSOLotto/PCSOLottoApp.swift`

- [ ] **Step 1: Create observable view model**

Create `ios_app/PCSOLotto/ViewModels/LotteryViewModel.swift`:

```swift
import Foundation

@MainActor
final class LotteryViewModel: ObservableObject {
    @Published var results: [LottoResult] = []
    @Published var games: [String] = []
    @Published var suggestions: [Suggestion] = []
    @Published var selectedAnalysis: GameAnalysis?
    @Published var isLoading = false
    @Published var errorMessage: String?

    private let repository: LotteryRepository

    init(repository: LotteryRepository = LotteryRepository()) {
        self.repository = repository
    }

    func loadHome() async {
        await load {
            async let fetchedResults = repository.fetchResults()
            async let fetchedGames = repository.fetchGames()
            async let fetchedSuggestions = repository.fetchSuggestions()
            results = try await fetchedResults
            games = try await fetchedGames
            suggestions = try await fetchedSuggestions
        }
    }

    func loadAnalysis(for game: String) async {
        await load {
            selectedAnalysis = try await repository.fetchAnalysis(for: game)
        }
    }

    private func load(_ operation: () async throws -> Void) async {
        isLoading = true
        errorMessage = nil
        do {
            try await operation()
        } catch {
            errorMessage = error.localizedDescription
        }
        isLoading = false
    }
}
```

- [ ] **Step 2: Create SwiftUI app and screens**

Create `ios_app/PCSOLotto/PCSOLottoApp.swift`:

```swift
import SwiftUI

@main
struct PCSOLottoApp: App {
    @StateObject private var viewModel = LotteryViewModel()

    var body: some Scene {
        WindowGroup {
            TabView {
                NavigationStack {
                    ResultsView(viewModel: viewModel)
                }
                .tabItem { Label("Results", systemImage: "list.bullet.rectangle") }

                NavigationStack {
                    SuggestionsView(viewModel: viewModel)
                }
                .tabItem { Label("Suggestions", systemImage: "sparkles") }
            }
            .task {
                await viewModel.loadHome()
            }
        }
    }
}
```

Create `ios_app/PCSOLotto/Views/ResultsView.swift`:

```swift
import SwiftUI

struct ResultsView: View {
    @ObservedObject var viewModel: LotteryViewModel
    @State private var query = ""

    private var filteredResults: [LottoResult] {
        if query.isEmpty { return viewModel.results }
        return viewModel.results.filter { $0.lottoGame.localizedCaseInsensitiveContains(query) }
    }

    var body: some View {
        List(filteredResults) { result in
            NavigationLink(value: result.lottoGame) {
                VStack(alignment: .leading, spacing: 6) {
                    Text(result.lottoGame).font(.headline)
                    Text(result.combinations).font(.title3).monospacedDigit()
                    Text("\(result.drawDate) • Jackpot \(result.jackpot) • Winners \(result.winners)")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
                .padding(.vertical, 4)
            }
        }
        .navigationTitle("PCSO Results")
        .searchable(text: $query, prompt: "Search game")
        .navigationDestination(for: String.self) { game in
            GameDetailView(game: game, viewModel: viewModel)
        }
        .overlay {
            if viewModel.isLoading {
                ProgressView("Loading")
            } else if let message = viewModel.errorMessage {
                ContentUnavailableView("Unable to Load", systemImage: "wifi.exclamationmark", description: Text(message))
            }
        }
    }
}
```

Create `ios_app/PCSOLotto/Views/GameDetailView.swift`:

```swift
import SwiftUI

struct GameDetailView: View {
    let game: String
    @ObservedObject var viewModel: LotteryViewModel

    private var gameResults: [LottoResult] {
        viewModel.results.filter { $0.lottoGame == game }
    }

    var body: some View {
        List {
            Section("Recent Draws") {
                ForEach(gameResults) { result in
                    VStack(alignment: .leading, spacing: 6) {
                        Text(result.combinations).font(.title3).monospacedDigit()
                        Text("\(result.drawDate) • Jackpot \(result.jackpot) • Winners \(result.winners)")
                            .font(.caption)
                            .foregroundStyle(.secondary)
                    }
                }
            }

            Section {
                NavigationLink("View Analysis") {
                    AnalysisView(game: game, viewModel: viewModel)
                }
            }
        }
        .navigationTitle(game)
    }
}
```

Create `ios_app/PCSOLotto/Views/AnalysisView.swift`:

```swift
import SwiftUI

struct AnalysisView: View {
    let game: String
    @ObservedObject var viewModel: LotteryViewModel

    var body: some View {
        List {
            if let analysis = viewModel.selectedAnalysis {
                if let stats = analysis.sumStatistics {
                    Section("Sum Statistics") {
                        LabeledContent("Draws", value: "\(stats.count)")
                        LabeledContent("Median", value: stats.median.formatted())
                        LabeledContent("Mean", value: stats.mean.formatted())
                        LabeledContent("Range", value: "\(stats.min.formatted()) - \(stats.max.formatted())")
                    }
                }

                Section("Number Frequency") {
                    ForEach(analysis.numberFrequency.prefix(20)) { item in
                        LabeledContent("\(item.number)", value: "\(item.frequency)")
                    }
                }

                Section("Odd / Even Patterns") {
                    ForEach(analysis.oddEvenPatterns) { item in
                        LabeledContent(item.pattern, value: "\(item.draws)")
                    }
                }
            } else if viewModel.isLoading {
                ProgressView("Loading analysis")
            }
        }
        .navigationTitle("Analysis")
        .task {
            await viewModel.loadAnalysis(for: game)
        }
    }
}
```

Create `ios_app/PCSOLotto/Views/SuggestionsView.swift`:

```swift
import SwiftUI

struct SuggestionsView: View {
    @ObservedObject var viewModel: LotteryViewModel

    var body: some View {
        List {
            Section {
                Text("Suggestions are based on historical patterns only. Lottery draws are random and these do not predict winning numbers.")
                    .font(.footnote)
                    .foregroundStyle(.secondary)
            }

            Section("Generated Combinations") {
                ForEach(viewModel.suggestions) { suggestion in
                    VStack(alignment: .leading, spacing: 6) {
                        Text(suggestion.lottoGame).font(.headline)
                        Text(suggestion.suggestedCombination).font(.title3).monospacedDigit()
                        Text("Sum \(suggestion.sum) • \(suggestion.oddEvenPattern) • Score \(suggestion.historicalFrequencyScore)")
                            .font(.caption)
                            .foregroundStyle(.secondary)
                    }
                    .padding(.vertical, 4)
                }
            }
        }
        .navigationTitle("Suggestions")
        .overlay {
            if viewModel.isLoading {
                ProgressView("Loading")
            } else if let message = viewModel.errorMessage {
                ContentUnavailableView("Unable to Load", systemImage: "wifi.exclamationmark", description: Text(message))
            }
        }
    }
}
```

- [ ] **Step 3: Commit**

```bash
git add ios_app/PCSOLotto
git commit -m "Add SwiftUI PCSO app screens"
```

## Task 6: Mobile App README and End-to-End Verification

**Files:**
- Create: `ios_app/PCSOLotto/README.md`
- Modify: `README.md`

- [ ] **Step 1: Add mobile README**

Create `ios_app/PCSOLotto/README.md`:

```markdown
# PCSO Lotto iOS App

This folder contains SwiftUI source files for the PCSO Lotto companion app.

## Local API

From the project root:

```bash
./pcso_env/bin/python -m mobile_api.app
```

The app defaults to:

```text
http://127.0.0.1:8080
```

When running on a physical iPhone, replace the base URL in `APIClient.swift` with the Mac's LAN IP address, for example:

```text
http://192.168.1.20:8080
```

## Xcode Setup

Create a new iOS App project in Xcode named `PCSOLotto`, using SwiftUI and Swift. Add the files in this folder to the app target, preserving the `Models`, `Services`, `ViewModels`, and `Views` groups.

The first app version expects the Python API to be running. Production API hosting and App Store submission are outside this first implementation.
```

- [ ] **Step 2: Update root README**

Add this section to `README.md` after `## Automated Pipeline`:

```markdown
## Mobile API and iOS App

This project includes a separated mobile layer:

- `mobile_api/` serves scraper and analysis outputs as JSON.
- `ios_app/PCSOLotto/` contains SwiftUI source files for the iPhone app.

Start the local mobile API:

```bash
./pcso_env/bin/python -m mobile_api.app
```

Then point the SwiftUI app to `http://127.0.0.1:8080` in the simulator, or to the Mac's LAN IP address when testing on a physical iPhone.
```

- [ ] **Step 3: Run backend verification**

Run: `./pcso_env/bin/python -m unittest tests.test_mobile_api_services tests.test_mobile_api_app -v`

Expected: PASS.

- [ ] **Step 4: Run API smoke check**

Run: `./pcso_env/bin/python -m mobile_api.app`

In a second terminal, run: `curl http://127.0.0.1:8080/api/results`

Expected: JSON response with a `results` array.

- [ ] **Step 5: Review Swift source for compile obviousness**

Run: `find ios_app/PCSOLotto -name '*.swift' -maxdepth 4 -print`

Expected: all Swift files listed under `Models`, `Services`, `ViewModels`, `Views`, plus `PCSOLottoApp.swift`.

- [ ] **Step 6: Commit**

```bash
git add README.md ios_app/PCSOLotto/README.md
git commit -m "Document mobile app setup"
```

## Self-Review

Spec coverage:
- Results viewer: covered by Tasks 1, 3, 4, and 5.
- Game detail: covered by Task 5.
- Analysis summaries: covered by Tasks 2, 3, 4, and 5.
- Suggestions and disclaimer: covered by Tasks 2, 3, 4, and 5.
- Backend API endpoints: covered by Task 3.
- Configurable development API URL: covered by Tasks 4 and 6.
- Error handling: covered by Tasks 1, 2, 3, and 5.
- Testing: backend tests are covered by Tasks 1 through 3 and end-to-end smoke checks by Task 6. Swift source verification is limited to source review because this plan does not generate a full Xcode project file.

Placeholder scan: the plan contains concrete file paths, commands, and code blocks for each implementation step.

Type consistency: endpoint JSON keys match Swift `CodingKeys`; service methods match repository calls; view model properties match view usage.
