import SwiftUI

@main
struct PCSOLottoApp: App {
    @StateObject private var viewModel = LotteryViewModel()

    var body: some Scene {
        WindowGroup {
            TabView {
                NavigationStack {
                    ResultsView(viewModel: viewModel)
                }
                .tabItem { Label("Results", systemImage: "list.bullet.rectangle") }

                NavigationStack {
                    SuggestionsView(viewModel: viewModel)
                }
                .tabItem { Label("Suggestions", systemImage: "sparkles") }
            }
            .task {
                await viewModel.loadHome()
            }
        }
    }
}
