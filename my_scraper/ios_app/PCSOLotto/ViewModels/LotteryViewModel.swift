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
