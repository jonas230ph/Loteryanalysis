import Foundation

// A single PCSO draw row displayed in the Results tab.
struct LottoResult: Identifiable, Codable, Hashable {
    // The API data does not include a unique id, so combine stable fields for
    // SwiftUI list identity.
    var id: String { "\(lottoGame)-\(drawDate)-\(combinations)" }
    let lottoGame: String
    let combinations: String
    let drawDate: String
    let jackpot: String
    let winners: String

    enum CodingKeys: String, CodingKey {
        case lottoGame = "lotto_game"
        case combinations
        case drawDate = "draw_date"
        case jackpot
        case winners
    }
}

// Wrapper matching the /api/results and /api/games/{game}/results JSON shape.
struct ResultsResponse: Codable {
    let results: [LottoResult]
}

// Wrapper matching the /api/games JSON shape.
struct GamesResponse: Codable {
    let games: [String]
}
