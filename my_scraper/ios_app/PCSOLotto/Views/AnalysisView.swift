import SwiftUI

// Breaks down historical patterns for a selected game.
struct AnalysisView: View {
    let game: String
    @ObservedObject var viewModel: LotteryViewModel

    var body: some View {
        List {
            if let analysis = viewModel.selectedAnalysis {
                if let stats = analysis.sumStatistics {
                    // Sum statistics describe the total of all drawn numbers.
                    Section("Sum Statistics") {
                        LabeledContent("Draws", value: "\(stats.count)")
                        LabeledContent("Median", value: stats.median.formatted())
                        LabeledContent("Mean", value: stats.mean.formatted())
                        LabeledContent("Range", value: "\(stats.min.formatted()) - \(stats.max.formatted())")
                    }
                }

                // Limit the list so the screen stays readable on iPhone.
                Section("Number Frequency") {
                    ForEach(analysis.numberFrequency.prefix(20)) { item in
                        LabeledContent("\(item.number)", value: "\(item.frequency)")
                    }
                }

                // Shows how often each odd/even distribution appeared.
                Section("Odd / Even Patterns") {
                    ForEach(analysis.oddEvenPatterns) { item in
                        LabeledContent(item.pattern, value: "\(item.draws)")
                    }
                }
            } else if viewModel.isLoading {
                ProgressView("Loading analysis")
            }
        }
        .navigationTitle("Analysis")
        .task {
            // Fetch analysis only after the user opens this screen.
            await viewModel.loadAnalysis(for: game)
        }
    }
}
