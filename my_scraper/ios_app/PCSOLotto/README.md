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

Create a new iOS App project in Xcode named `PCSOLotto`, using SwiftUI and Swift. Add the files in this folder to the app target, preserving the `Models`, `Services`, `ViewModels`, and `Views` groups.

The first app version expects the Python API to be running. Production API hosting and App Store submission are outside this first implementation.
