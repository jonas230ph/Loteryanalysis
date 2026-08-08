import Foundation

// A generated combination suggestion shown in the Suggestions tab.
struct Suggestion: Identifiable, Codable, Hashable {
    // Suggestions are unique enough by game plus generated combination.
    var id: String { "\(lottoGame)-\(suggestedCombination)" }
    let lottoGame: String
    let suggestedCombination: String
    let sum: Int
    let oddEvenPattern: String
    let historicalFrequencyScore: Int
    let basis: String

    enum CodingKeys: String, CodingKey {
        case lottoGame = "lotto_game"
        case suggestedCombination = "suggested_combination"
        case sum
        case oddEvenPattern = "odd_even_pattern"
        case historicalFrequencyScore = "historical_frequency_score"
        case basis
    }
}

// Wrapper matching the /api/suggestions JSON shape.
struct SuggestionsResponse: Codable {
    let suggestions: [Suggestion]
}
