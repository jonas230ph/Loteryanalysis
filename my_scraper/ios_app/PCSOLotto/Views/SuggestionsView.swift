import SwiftUI

// Displays generated combinations from the latest pipeline output.
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
            // Refresh button runs the same full refresh path as pull-to-refresh.
            ToolbarItem(placement: .topBarTrailing) {
                Button {
                    Task {
                        await viewModel.refreshHome()
                    }
                } label: {
                    Image(systemName: "arrow.clockwise")
                }
                .accessibilityLabel("Refresh suggestions")
            }
        }
        .refreshable {
            // Pulling down starts the hosted pipeline and reloads known data.
            await viewModel.refreshHome()
        }
        .overlay {
            // Keep the prior suggestions visible while showing load or error state.
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
