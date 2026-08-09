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

// Focused Ultra Lotto report using the moving four-week odd/even basis.
struct UltraTrendsView: View {
    @ObservedObject var viewModel: LotteryViewModel

    var body: some View {
        List {
            if let leadingPattern = viewModel.ultraLottoTrends.oddEvenPatterns.first {
                Section("Moving Four-Week Odd / Even Basis") {
                    LabeledContent("Leading pattern", value: leadingPattern.pattern)
                    LabeledContent("Draws", value: "\(leadingPattern.draws) of \(leadingPattern.movingWindowDraws)")
                    LabeledContent("Period", value: "\(leadingPattern.movingWindowStart) to \(leadingPattern.movingWindowEnd)")
                }

                Section("Other Recent Patterns") {
                    ForEach(viewModel.ultraLottoTrends.oddEvenPatterns.dropFirst()) { pattern in
                        LabeledContent(pattern.pattern, value: "\(pattern.draws) draws")
                    }
                }

                Section("Historical Trend Samples") {
                    ForEach(viewModel.ultraLottoTrends.suggestions) { suggestion in
                        VStack(alignment: .leading, spacing: 6) {
                            Text(suggestion.suggestedCombination).font(.title3).monospacedDigit()
                            Text("\(suggestion.oddCount) odd - \(suggestion.evenCount) even - Sum \(suggestion.sum)")
                                .font(.caption)
                                .foregroundStyle(.secondary)
                            Text(suggestion.basis)
                                .font(.caption2)
                                .foregroundStyle(.secondary)
                        }
                        .padding(.vertical, 4)
                    }
                }
            } else if !viewModel.isLoading {
                ContentUnavailableView(
                    "Trend Report Unavailable",
                    systemImage: "chart.bar.xaxis",
                    description: Text("Refresh after the latest analysis finishes publishing.")
                )
            }
        }
        .navigationTitle("Ultra Trends")
        .toolbar {
            ToolbarItem(placement: .topBarTrailing) {
                Button {
                    Task {
                        await viewModel.refreshHome()
                    }
                } label: {
                    Image(systemName: "arrow.clockwise")
                }
                .accessibilityLabel("Refresh Ultra Lotto trends")
            }
        }
        .refreshable {
            await viewModel.refreshHome()
        }
        .overlay {
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
