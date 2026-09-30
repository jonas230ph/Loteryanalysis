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
    @AppStorage("ultraLottoCheckerEntries") private var savedEnteredNumbers = ""
    @State private var enteredNumbers = ["", "", ""]
    @State private var checkResults: [String?] = [nil, nil, nil]
    @State private var invalidInputs = [false, false, false]
    @State private var matchedValues = [[Int](), [Int](), [Int]()]

    var body: some View {
        List {
            Section("Check Latest Ultra Lotto Draw") {
                if let latestUltraResult {
                    LabeledContent("Latest draw", value: latestUltraResult.drawDate)
                    Text(latestUltraResult.combinations).monospacedDigit()
                    ForEach(enteredNumbers.indices, id: \.self) { slot in
                        TextField("Enter 6 numbers", text: $enteredNumbers[slot])
                            .keyboardType(.numbersAndPunctuation)
                            .textInputAutocapitalization(.never)
                        Button("Check Set \(slot + 1)") {
                            checkNumbers(at: slot, against: latestUltraResult)
                        }
                        if let checkResult = checkResults[slot] {
                            if invalidInputs[slot] {
                                Text(checkResult).foregroundStyle(.red)
                            } else if !matchedValues[slot].isEmpty {
                                let matchedText = matchedValues[slot]
                                    .map { String(format: "%02d", $0) }
                                    .joined(separator: ", ")
                                Text("Matched \(matchedValues[slot].count): ") +
                                    Text(matchedText).bold().foregroundStyle(.red)
                            } else {
                                Text(checkResult)
                            }
                        }
                        Button(role: .destructive) {
                            clearChecker(at: slot)
                        } label: {
                            Label("Clear Set \(slot + 1)", systemImage: "trash")
                        }
                    }
                    Button(role: .destructive) {
                        clearAllCheckers()
                    } label: {
                        Label("Clear All", systemImage: "trash")
                    }
                } else {
                    Text("Latest Ultra Lotto result is loading.")
                        .foregroundStyle(.secondary)
                }
            }

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
        .onAppear {
            restoreEnteredNumbers()
        }
        .onChange(of: enteredNumbers) { _, values in
            savedEnteredNumbers = values.joined(separator: "\u{1F}")
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

    private var latestUltraResult: LottoResult? {
        viewModel.results.first { $0.lottoGame == "Ultra Lotto 6/58" }
    }

    private func checkNumbers(at slot: Int, against result: LottoResult) {
        let submittedNumbers = numbers(from: enteredNumbers[slot])
        guard submittedNumbers.count == 6,
              Set(submittedNumbers).count == 6,
              submittedNumbers.allSatisfy({ (1...58).contains($0) }) else {
            invalidInputs[slot] = true
            matchedValues[slot] = []
            checkResults[slot] = "Enter six different numbers from 1 to 58."
            return
        }

        let matchedNumbers = Set(submittedNumbers)
            .intersection(Set(numbers(from: result.combinations)))
            .sorted()
        invalidInputs[slot] = false
        matchedValues[slot] = matchedNumbers
        let matchedText = matchedNumbers.map { String(format: "%02d", $0) }.joined(separator: ", ")
        checkResults[slot] = matchedNumbers.isEmpty
            ? "Matched 0 numbers against the \(result.drawDate) draw."
            : "Matched \(matchedNumbers.count): \(matchedText)"
    }

    private func numbers(from value: String) -> [Int] {
        value.split(whereSeparator: { !$0.isNumber }).compactMap { Int($0) }
    }

    private func clearChecker(at slot: Int) {
        enteredNumbers[slot] = ""
        checkResults[slot] = nil
        invalidInputs[slot] = false
        matchedValues[slot] = []
    }

    private func clearAllCheckers() {
        for slot in enteredNumbers.indices {
            clearChecker(at: slot)
        }
    }

    private func restoreEnteredNumbers() {
        let savedValues = savedEnteredNumbers.components(separatedBy: "\u{1F}")
        enteredNumbers = enteredNumbers.indices.map {
            savedValues.indices.contains($0) ? savedValues[$0] : ""
        }
    }
}
