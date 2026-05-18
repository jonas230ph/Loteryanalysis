import Foundation

struct LottoResult: Identifiable, Codable, Hashable {
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

struct ResultsResponse: Codable {
    let results: [LottoResult]
}

struct GamesResponse: Codable {
    let games: [String]
}
