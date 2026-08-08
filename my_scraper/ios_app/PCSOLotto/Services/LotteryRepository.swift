import Foundation

// App-facing data layer. Views talk to this repository instead of knowing API
// route strings directly.
final class LotteryRepository {
    private let client: APIClient

    init(client: APIClient = APIClient()) {
        self.client = client
    }

    func fetchResults() async throws -> [LottoResult] {
        // Home screen list of all recent draw results.
        let response: ResultsResponse = try await client.get("api/results")
        return response.results
    }

    func fetchGames() async throws -> [String] {
        // Game names are used for navigation and filtering.
        let response: GamesResponse = try await client.get("api/games")
        return response.games
    }

    func fetchResults(for game: String) async throws -> [LottoResult] {
        // Encode the game name because values like "6/58" contain a slash.
        let encoded = encodedPathComponent(game)
        let response: ResultsResponse = try await client.get("api/games/\(encoded)/results")
        return response.results
    }

    func fetchAnalysis(for game: String) async throws -> GameAnalysis {
        // Analysis is loaded only when the user opens the detail screen.
        let encoded = encodedPathComponent(game)
        let response: AnalysisResponse = try await client.get("api/games/\(encoded)/analysis")
        return response.analysis
    }

    func fetchSuggestions() async throws -> [Suggestion] {
        // Generated combinations shown in the Suggestions tab.
        let response: SuggestionsResponse = try await client.get("api/suggestions")
        return response.suggestions
    }

    func refreshData() async throws -> RefreshResponse {
        // Koyeb starts the GitHub Actions job. The current snapshot remains
        // readable while its next version is being scraped and analyzed.
        guard let refreshKey = Bundle.main.object(forInfoDictionaryKey: "REFRESH_REQUEST_KEY") as? String,
              !refreshKey.isEmpty,
              !refreshKey.contains("REPLACE_WITH") else {
            throw APIClientError.serverMessage("App refresh is not configured.")
        }
        let response: RefreshResponse = try await client.post(
            "api/refresh",
            headers: ["X-PCSO-Refresh-Key": refreshKey]
        )
        return response
    }

    private func encodedPathComponent(_ value: String) -> String {
        // Keep "/" encoded so it stays inside the game name instead of becoming
        // another URL path segment.
        var allowed = CharacterSet.urlPathAllowed
        allowed.remove(charactersIn: "/")
        return value.addingPercentEncoding(withAllowedCharacters: allowed) ?? value
    }
}

// Success payload returned by POST /api/refresh.
struct RefreshResponse: Codable {
    let status: String
    let message: String?
}
