import SwiftUI

// Shows recent draws for one selected lottery game.
struct GameDetailView: View {
    let game: String
    @ObservedObject var viewModel: LotteryViewModel

    private var gameResults: [LottoResult] {
        // Results are already loaded on the home screen, so the detail view can
        // filter locally without another network request.
        viewModel.results.filter { $0.lottoGame == game }
    }

    var body: some View {
        List {
            Section("Recent Draws") {
                ForEach(gameResults) { result in
                    VStack(alignment: .leading, spacing: 6) {
                        Text(result.combinations).font(.title3).monospacedDigit()
                        Text("\(result.drawDate) - Jackpot \(result.jackpot) - Winners \(result.winners)")
                            .font(.caption)
                            .foregroundStyle(.secondary)
                    }
                }
            }

            Section {
                // Analysis loads on demand when this link is opened.
                NavigationLink("View Analysis") {
                    AnalysisView(game: game, viewModel: viewModel)
                }
            }
        }
        .navigationTitle(game)
    }
}
