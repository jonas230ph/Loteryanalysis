# PCSO Lotto iOS App

This folder contains SwiftUI source files for the PCSO Lotto companion app.

## Local API

From the project root:

```bash
./pcso_env/bin/python -m mobile_api.app
```

The app defaults to:

```text
http://127.0.0.1:8080
```

When running on a physical iPhone, replace the base URL in `Services/APIClient.swift` with the Mac's LAN IP address, for example:

```text
http://192.168.1.20:8080
```

Find the Mac's Wi-Fi IP with:

```bash
ipconfig getifaddr en0
```

Make sure the Mac and iPhone are on the same Wi-Fi network, and allow local network access if iOS prompts for it.

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

Both actions refetch data from the running Python API.

When the app is pointed at Railway, refresh first calls:

```text
POST /api/refresh
```

The Railway API runs the scraper/analysis pipeline and then the app reloads results and suggestions. No MacBook-local path is used.

To update the underlying data before refreshing the app:

```bash
./pcso_env/bin/python pcso_lottery_scraper.py
./pcso_env/bin/python analyze_pcso_results.py
```

Then keep or restart the API:

```bash
./pcso_env/bin/python -m mobile_api.app
```

## Install On iPhone

1. Connect the iPhone to the Mac by cable, or enable wireless debugging in Xcode.
2. Open `PCSOLotto.xcodeproj` in Xcode.
3. Select your iPhone as the run destination.
4. Update `Services/APIClient.swift` to use the Mac's LAN IP instead of `127.0.0.1`.
5. Start the Python API on the Mac.
6. Press Run in Xcode.
7. If prompted, trust the developer profile on the iPhone in Settings.

The first app version expects the Python API to be running. Production API hosting and App Store submission are outside this first implementation.
