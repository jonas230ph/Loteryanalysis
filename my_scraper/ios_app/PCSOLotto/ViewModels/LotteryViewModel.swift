import SwiftUI

// Shared screen state for the Results, Suggestions, and Analysis views.
@MainActor
final class LotteryViewModel: ObservableObject {
    // Published properties automatically update SwiftUI when network data changes.
    @Published var results: [LottoResult] = []
    @Published var games: [String] = []
    @Published var suggestions: [Suggestion] = []
    @Published var ultraLottoTrends: UltraLottoTrend = .empty
    @Published var selectedAnalysis: GameAnalysis?
    @Published var isLoading = false
    @Published var errorMessage: String?
    @Published var refreshMessage: String?

    private let repository: LotteryRepository

    init(repository: LotteryRepository = LotteryRepository()) {
        self.repository = repository
    }

    func loadHome() async {
        // Initial load reads the latest snapshot from Render.
        await load {
            try await loadHomeData()
        }
    }

    func refreshHome() async {
        // Pull-to-refresh starts the remote job, then keeps the visible data
        // current until GitHub Actions finishes publishing the next snapshot.
        await load {
            let response = try await repository.refreshData()
            try await loadHomeData()
            refreshMessage = response.message
        }
    }

    func loadAnalysis(for game: String) async {
        // Analysis is separate so normal app launch stays fast.
        await load {
            selectedAnalysis = try await repository.fetchAnalysis(for: game)
        }
    }

    private func load(_ operation: () async throws -> Void) async {
        // One loading helper keeps the spinner and error handling consistent.
        isLoading = true
        errorMessage = nil
        do {
            try await operation()
        } catch {
            errorMessage = error.localizedDescription
        }
        isLoading = false
    }

    private func loadHomeData() async throws {
        // Fetch independent home data in parallel to reduce wait time.
        async let fetchedResults = repository.fetchResults()
        async let fetchedGames = repository.fetchGames()
        async let fetchedSuggestions = repository.fetchSuggestions()
        async let fetchedUltraTrends = repository.fetchUltraLottoTrends()
        results = try await fetchedResults
        games = try await fetchedGames
        suggestions = try await fetchedSuggestions
        // A new app can open against a temporarily older API deployment.
        ultraLottoTrends = (try? await fetchedUltraTrends) ?? .empty
    }
}
