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

When running on a physical iPhone, replace the base URL in `APIClient.swift` with the Mac's LAN IP address, for example:

```text
http://192.168.1.20:8080
```

## Xcode Setup

Open this project in Xcode:

```text
PCSOLotto.xcodeproj
```

The project includes the app target and the SwiftUI files in this folder.

The first app version expects the Python API to be running. Production API hosting and App Store submission are outside this first implementation.
