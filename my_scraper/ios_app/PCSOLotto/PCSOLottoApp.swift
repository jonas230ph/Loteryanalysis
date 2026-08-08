import SwiftUI

@main
struct PCSOLottoApp: App {
    // One shared view model keeps both tabs showing the same latest API data.
    @StateObject private var viewModel = LotteryViewModel()

    var body: some Scene {
        WindowGroup {
            TabView {
                // Results tab starts with a navigation stack so each game can
                // push into its detail and analysis screens.
                NavigationStack {
                    ResultsView(viewModel: viewModel)
                }
                .tabItem { Label("Results", systemImage: "list.bullet.rectangle") }

                // Suggestions stays in its own stack so tab navigation remains
                // independent from the Results screen.
                NavigationStack {
                    SuggestionsView(viewModel: viewModel)
                }
                .tabItem { Label("Suggestions", systemImage: "sparkles") }
            }
            .task {
                // Load data once when the app first appears.
                await viewModel.loadHome()
            }
        }
    }
}
