import Foundation

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

struct NumberFrequency: Identifiable, Codable, Hashable {
    var id: Int { number }
    let number: Int
    let frequency: Int
}

struct OddEvenPattern: Identifiable, Codable, Hashable {
    var id: String { pattern }
    let pattern: String
    let draws: Int
}

struct SumStatistics: Codable, Hashable {
    let count: Int
    let min: Double
    let median: Double
    let mean: Double
    let max: Double
    let std: Double
}

struct AnalysisResponse: Codable {
    let analysis: GameAnalysis
}
