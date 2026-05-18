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
                        Text("\(result.drawDate) - Jackpot \(result.jackpot) - Winners \(result.winners)")
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
