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
                        Text("Sum \(suggestion.sum) - \(suggestion.oddEvenPattern) - Score \(suggestion.historicalFrequencyScore)")
                            .font(.caption)
                            .foregroundStyle(.secondary)
                    }
                    .padding(.vertical, 4)
                }
            }
        }
        .navigationTitle("Suggestions")
        .toolbar {
            ToolbarItem(placement: .topBarTrailing) {
                Button {
                    Task {
                        await viewModel.loadHome()
                    }
                } label: {
                    Image(systemName: "arrow.clockwise")
                }
                .accessibilityLabel("Refresh suggestions")
            }
        }
        .refreshable {
            await viewModel.loadHome()
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
