import Foundation

// Analysis shown on the game detail screen. The API sends snake_case keys, so
// CodingKeys map them into Swift's camelCase property names.
struct GameAnalysis: Codable, Hashable {
    let lottoGame: String
    let numberFrequency: [NumberFrequency]
    let oddEvenPatterns: [OddEvenPattern]
    let sumStatistics: SumStatistics?

    enum CodingKeys: String, CodingKey {
        case lottoGame = "lotto_game"
        case numberFrequency = "number_frequency"
        case oddEvenPatterns = "odd_even_patterns"
        case sumStatistics = "sum_statistics"
    }
}

// One lottery number and how often it appeared historically.
struct NumberFrequency: Identifiable, Codable, Hashable {
    var id: Int { number }
    let number: Int
    let frequency: Int
}

// Count of odd/even draw patterns, such as "3 Odd / 3 Even".
struct OddEvenPattern: Identifiable, Codable, Hashable {
    var id: String { pattern }
    let pattern: String
    let draws: Int
}

// Summary of the number totals for a game's previous draws.
struct SumStatistics: Codable, Hashable {
    let count: Int
    let min: Double
    let median: Double
    let mean: Double
    let max: Double
    let std: Double
}

// Wrapper matching the /api/games/{game}/analysis JSON shape.
struct AnalysisResponse: Codable {
    let analysis: GameAnalysis
}
