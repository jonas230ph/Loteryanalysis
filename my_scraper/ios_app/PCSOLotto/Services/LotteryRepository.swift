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
        let encoded = encodedPathComponent(game)
        let response: ResultsResponse = try await client.get("api/games/\(encoded)/results")
        return response.results
    }

    func fetchAnalysis(for game: String) async throws -> GameAnalysis {
        let encoded = encodedPathComponent(game)
        let response: AnalysisResponse = try await client.get("api/games/\(encoded)/analysis")
        return response.analysis
    }

    func fetchSuggestions() async throws -> [Suggestion] {
        let response: SuggestionsResponse = try await client.get("api/suggestions")
        return response.suggestions
    }

    private func encodedPathComponent(_ value: String) -> String {
        var allowed = CharacterSet.urlPathAllowed
        allowed.remove(charactersIn: "/")
        return value.addingPercentEncoding(withAllowedCharacters: allowed) ?? value
    }
}
