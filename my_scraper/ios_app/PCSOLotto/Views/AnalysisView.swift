import SwiftUI

struct AnalysisView: View {
    let game: String
    @ObservedObject var viewModel: LotteryViewModel

    var body: some View {
        List {
            if let analysis = viewModel.selectedAnalysis {
                if let stats = analysis.sumStatistics {
                    Section("Sum Statistics") {
                        LabeledContent("Draws", value: "\(stats.count)")
                        LabeledContent("Median", value: stats.median.formatted())
                        LabeledContent("Mean", value: stats.mean.formatted())
                        LabeledContent("Range", value: "\(stats.min.formatted()) - \(stats.max.formatted())")
                    }
                }

                Section("Number Frequency") {
                    ForEach(analysis.numberFrequency.prefix(20)) { item in
                        LabeledContent("\(item.number)", value: "\(item.frequency)")
                    }
                }

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
            await viewModel.loadAnalysis(for: game)
        }
    }
}
