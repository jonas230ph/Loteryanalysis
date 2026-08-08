import Foundation

// Errors that can be shown directly in SwiftUI when the API fails.
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

// Standard error payload returned by the Python mobile API.
struct APIErrorResponse: Codable {
    let error: String
}

// Thin networking wrapper for the Render-hosted PCSO mobile API.
final class APIClient {
    let baseURL: URL
    private let session: URLSession
    private let decoder: JSONDecoder

    init(baseURL: URL? = nil, session: URLSession = .shared) {
        // API_BASE_URL is set once in the Xcode build settings after Render
        // deploys. It keeps a physical iPhone independent of the MacBook LAN.
        let configuredURL = Bundle.main.object(forInfoDictionaryKey: "API_BASE_URL") as? String
        let resolvedURL = baseURL ?? URL(string: configuredURL ?? "") ?? URL(string: "https://example.invalid")!
        // Normalizing to a trailing slash keeps relative paths like "api/results"
        // from accidentally replacing the host path.
        if resolvedURL.absoluteString.hasSuffix("/") {
            self.baseURL = resolvedURL
        } else {
            self.baseURL = URL(string: resolvedURL.absoluteString + "/")!
        }
        self.session = session
        self.decoder = JSONDecoder()
    }

    func get<T: Decodable>(_ path: String) async throws -> T {
        // GET routes load the current published data from Render.
        guard let url = URL(string: path, relativeTo: baseURL)?.absoluteURL else {
            throw APIClientError.invalidResponse
        }
        let (data, response) = try await session.data(from: url)
        return try decode(data: data, response: response)
    }

    func post<T: Decodable>(_ path: String, headers: [String: String] = [:]) async throws -> T {
        // POST starts the remote GitHub Actions refresh workflow.
        guard let url = URL(string: path, relativeTo: baseURL)?.absoluteURL else {
            throw APIClientError.invalidResponse
        }
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        headers.forEach { name, value in
            request.setValue(value, forHTTPHeaderField: name)
        }
        let (data, response) = try await session.data(for: request)
        return try decode(data: data, response: response)
    }

    private func decode<T: Decodable>(data: Data, response: URLResponse) throws -> T {
        // Convert non-2xx API responses into a readable message for the app.
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
