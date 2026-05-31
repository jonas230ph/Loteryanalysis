import Foundation

enum APIClientError: Error, LocalizedError {
    case invalidResponse
    case serverMessage(String)

    var errorDescription: String? {
        switch self {
        case .invalidResponse:
            return "The server returned an invalid response."
        case .serverMessage(let message):
            return message
        }
    }
}

struct APIErrorResponse: Codable {
    let error: String
}

final class APIClient {
    let baseURL: URL
    private let session: URLSession
    private let decoder: JSONDecoder

    init(baseURL: URL = URL(string: "https://loteryanalysis-production.up.railway.app")!, session: URLSession = .shared) {
        if baseURL.absoluteString.hasSuffix("/") {
            self.baseURL = baseURL
        } else {
            self.baseURL = URL(string: baseURL.absoluteString + "/")!
        }
        self.session = session
        self.decoder = JSONDecoder()
    }

    func get<T: Decodable>(_ path: String) async throws -> T {
        guard let url = URL(string: path, relativeTo: baseURL)?.absoluteURL else {
            throw APIClientError.invalidResponse
        }
        let (data, response) = try await session.data(from: url)
        return try decode(data: data, response: response)
    }

    func post<T: Decodable>(_ path: String) async throws -> T {
        guard let url = URL(string: path, relativeTo: baseURL)?.absoluteURL else {
            throw APIClientError.invalidResponse
        }
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        let (data, response) = try await session.data(for: request)
        return try decode(data: data, response: response)
    }

    private func decode<T: Decodable>(data: Data, response: URLResponse) throws -> T {
        guard let httpResponse = response as? HTTPURLResponse else {
            throw APIClientError.invalidResponse
        }
        guard (200..<300).contains(httpResponse.statusCode) else {
            let apiError = try? decoder.decode(APIErrorResponse.self, from: data)
            throw APIClientError.serverMessage(apiError?.error ?? "Request failed.")
        }
        return try decoder.decode(T.self, from: data)
    }
}
