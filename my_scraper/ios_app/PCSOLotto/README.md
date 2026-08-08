# PCSO Lotto iOS App

This folder contains SwiftUI source files for the PCSO Lotto companion app.

## Hosted API

The physical iPhone uses the public Render HTTPS API. In Xcode, select the
PCSOLotto target, open **Build Settings**, and set `API_BASE_URL` to the
deployed `https://...onrender.com` URL. Set `REFRESH_REQUEST_KEY` to the same random
value held by Render. Do not include a port number.

For simulator-only local development, you may pass a custom API URL when
constructing `APIClient` in a debug build.

## Xcode Setup

Open this project in Xcode:

```text
PCSOLotto.xcodeproj
```

The project includes the app target and the SwiftUI files in this folder.

## Refreshing Data

The Results and Suggestions tabs support:

- Pull down on the list to refresh.
- Tap the refresh icon in the top-right toolbar.

Both actions start a remote refresh and refetch the most recently published
snapshot from the Render API. Refresh calls:

```text
POST /api/refresh
```

Render starts the GitHub Actions workflow. The workflow runs the Python
scraper and analyzer, then replaces the Supabase snapshot. No MacBook-local path
is used.

## Install On iPhone

1. Connect the iPhone to the Mac by cable, or enable wireless debugging in Xcode.
2. Open `PCSOLotto.xcodeproj` in Xcode.
3. Select your iPhone as the run destination.
4. Set `API_BASE_URL` and `REFRESH_REQUEST_KEY` in the target Build Settings.
5. Press Run in Xcode.
6. If prompted, trust the developer profile on the iPhone in Settings.

The app does not require a Python process to be running on the MacBook.
