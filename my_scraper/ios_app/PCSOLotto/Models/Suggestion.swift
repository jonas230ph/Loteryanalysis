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

// Focused Ultra Lotto data shown in the dedicated Trends tab.
struct UltraLottoTrend: Codable {
    let oddEvenPatterns: [UltraOddEvenPattern]
    let suggestions: [UltraTrendSuggestion]

    static let empty = UltraLottoTrend(oddEvenPatterns: [], suggestions: [])

    enum CodingKeys: String, CodingKey {
        case oddEvenPatterns = "odd_even_patterns"
        case suggestions
    }
}

struct UltraOddEvenPattern: Identifiable, Codable, Hashable {
    let rank: Int
    let pattern: String
    let draws: Int
    let drawPercentage: Double
    let movingWindowDays: Int
    let movingWindowStart: String
    let movingWindowEnd: String
    let movingWindowDraws: Int

    var id: Int { rank }

    enum CodingKeys: String, CodingKey {
        case rank, pattern, draws
        case drawPercentage = "draw_percentage"
        case movingWindowDays = "moving_window_days"
        case movingWindowStart = "moving_window_start"
        case movingWindowEnd = "moving_window_end"
        case movingWindowDraws = "moving_window_draws"
    }
}

struct UltraTrendSuggestion: Identifiable, Codable, Hashable {
    let rank: Int
    let suggestedCombination: String
    let oddCount: Int
    let evenCount: Int
    let sum: Int
    let trendScore: Double
    let matchesRecentSumRange: Bool
    let basis: String

    var id: Int { rank }

    enum CodingKeys: String, CodingKey {
        case rank, sum, basis
        case suggestedCombination = "suggested_combination"
        case oddCount = "odd_count"
        case evenCount = "even_count"
        case trendScore = "trend_score"
        case matchesRecentSumRange = "matches_recent_sum_range"
    }
}

struct UltraLottoTrendResponse: Codable {
    let oddEvenPatterns: [UltraOddEvenPattern]
    let suggestions: [UltraTrendSuggestion]

    func asTrend() -> UltraLottoTrend {
        UltraLottoTrend(oddEvenPatterns: oddEvenPatterns, suggestions: suggestions)
    }

    enum CodingKeys: String, CodingKey {
        case oddEvenPatterns = "odd_even_patterns"
        case suggestions
    }
}
