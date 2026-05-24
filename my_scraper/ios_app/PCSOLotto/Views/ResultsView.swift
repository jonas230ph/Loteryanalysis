import SwiftUI

struct ResultsView: View {
    @ObservedObject var viewModel: LotteryViewModel
    @State private var query = ""

    private var filteredResults: [LottoResult] {
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
            ToolbarItem(placement: .topBarTrailing) {
                Button {
                    Task {
                        await viewModel.loadHome()
                    }
                } label: {
                    Image(systemName: "arrow.clockwise")
                }
                .accessibilityLabel("Refresh results")
            }
        }
        .searchable(text: $query, prompt: "Search game")
        .refreshable {
            await viewModel.loadHome()
        }
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
