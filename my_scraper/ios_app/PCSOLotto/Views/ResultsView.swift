import SwiftUI

// Main list of latest PCSO draw results.
struct ResultsView: View {
    @ObservedObject var viewModel: LotteryViewModel
    @State private var query = ""

    private var filteredResults: [LottoResult] {
        // Search filters by game name while keeping the full list in the view model.
        if query.isEmpty {
            return viewModel.results
        }
        return viewModel.results.filter { $0.lottoGame.localizedCaseInsensitiveContains(query) }
    }

    var body: some View {
        List(filteredResults) { result in
            NavigationLink(value: result.lottoGame) {
                VStack(alignment: .leading, spacing: 6) {
                    Text(result.lottoGame).font(.headline)
                    Text(result.combinations).font(.title3).monospacedDigit()
                    Text("\(result.drawDate) - Jackpot \(result.jackpot) - Winners \(result.winners)")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
                .padding(.vertical, 4)
            }
        }
        .navigationTitle("PCSO Results")
        .toolbar {
            // Toolbar refresh matches pull-to-refresh for users who prefer a
            // visible button.
            ToolbarItem(placement: .topBarTrailing) {
                Button {
                    Task {
                        await viewModel.refreshHome()
                    }
                } label: {
                    Image(systemName: "arrow.clockwise")
                }
                .accessibilityLabel("Refresh results")
            }
        }
        .searchable(text: $query, prompt: "Search game")
        .refreshable {
            // Pulling down starts the hosted pipeline and reloads known data.
            await viewModel.refreshHome()
        }
        .navigationDestination(for: String.self) { game in
            // The NavigationLink value is the game name.
            GameDetailView(game: game, viewModel: viewModel)
        }
        .overlay {
            // Show loading/error state above the list without replacing the
            // previous data immediately.
            if viewModel.isLoading {
                ProgressView("Loading")
            } else if let message = viewModel.errorMessage {
                ContentUnavailableView("Unable to Load", systemImage: "wifi.exclamationmark", description: Text(message))
            }
        }
        .alert("Refresh Started", isPresented: Binding(
            get: { viewModel.refreshMessage != nil },
            set: { if !$0 { viewModel.refreshMessage = nil } }
        )) {
            Button("OK", role: .cancel) { viewModel.refreshMessage = nil }
        } message: {
            Text(viewModel.refreshMessage ?? "")
        }
    }
}
