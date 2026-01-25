import Cocoa

// MARK: - App Delegate

class AppDelegate: NSObject, NSApplicationDelegate {
    private var statusItem: NSStatusItem!
    private var progressWindow = ProgressWindowController()
    private var configWindow: ConfigWindowController?
    private var mainPanel: MainPanelController?

    private var isDownloading = false
    private var isTranscribing = false
    private var animationTimer: Timer?
    private var animationFrame = 0

    // MARK: - Lifecycle

    func applicationDidFinishLaunching(_ notification: Notification) {
        // Create download folder
        try? FileManager.default.createDirectory(atPath: Paths.downloadBase, withIntermediateDirectories: true)
        try? FileManager.default.createDirectory(atPath: Paths.configDir, withIntermediateDirectories: true)
        try? FileManager.default.createDirectory(atPath: Paths.stateDir, withIntermediateDirectories: true)

        // Setup status bar
        statusItem = NSStatusBar.system.statusItem(withLength: NSStatusItem.variableLength)
        statusItem.autosaveName = "GoogleMediaBackupStatusItem"
        updateStatusIcon()
        setupMenu()

        // Setup callbacks
        setupDownloadCallbacks()
        setupTranscriptionCallbacks()

        // Setup main panel
        setupMainPanel()

        // Check auto-download
        let config = ConfigManager.shared.loadConfig()
        if config.autoDownload && GoogleAuthManager.shared.status.isReady {
            DispatchQueue.main.asyncAfter(deadline: .now() + 1) { [weak self] in
                self?.startDownload()
            }
        }
    }

    // MARK: - Main Panel Setup

    private func setupMainPanel() {
        mainPanel = MainPanelController()

        mainPanel?.onStartDownload = { [weak self] in
            self?.startDownload()
        }

        mainPanel?.onStopDownload = { [weak self] in
            self?.stopDownload()
        }

        mainPanel?.onStartTranscription = { [weak self] in
            self?.startTranscription()
        }

        mainPanel?.onOpenDownloads = { [weak self] in
            self?.openDownloadsFolder()
        }

        mainPanel?.onOpenConfig = { [weak self] in
            self?.openConfig()
        }

        mainPanel?.onSignIn = { [weak self] in
            self?.signIn()
        }
    }

    // MARK: - Download Callbacks

    private func setupDownloadCallbacks() {
        DownloadManager.shared.onStatusChanged = { [weak self] status in
            DispatchQueue.main.async {
                self?.isDownloading = status.isActive
                self?.updateStatusIcon()
                self?.setupMenu()
                self?.mainPanel?.refresh()

                if case .completed(let downloaded, _, _) = status {
                    if downloaded > 0 {
                        // Auto-transcribe if enabled
                        let config = ConfigManager.shared.loadConfig()
                        if config.autoTranscribe {
                            self?.startTranscription()
                        }
                    }
                }
            }
        }

        DownloadManager.shared.onProgress = { [weak self] message in
            DispatchQueue.main.async {
                self?.progressWindow.update(message: message)
            }
        }
    }

    // MARK: - Transcription Callbacks

    private func setupTranscriptionCallbacks() {
        TranscriptionManager.shared.onStatusChanged = { [weak self] status in
            DispatchQueue.main.async {
                self?.isTranscribing = status.isTranscribing
                self?.updateStatusIcon()
                self?.setupMenu()
                self?.mainPanel?.refresh()
            }
        }

        TranscriptionManager.shared.onProgress = { [weak self] message in
            DispatchQueue.main.async {
                self?.progressWindow.update(message: message)
            }
        }
    }

    // MARK: - Status Icon

    private func updateStatusIcon() {
        guard let button = statusItem.button else { return }

        if isDownloading || isTranscribing {
            // Animated icon
            let icons = ["arrow.down.circle", "arrow.down.circle.fill"]
            let iconName = icons[animationFrame % icons.count]
            if let image = NSImage(systemSymbolName: iconName, accessibilityDescription: "Downloading") {
                let config = NSImage.SymbolConfiguration(paletteColors: [.systemBlue])
                button.image = image.withSymbolConfiguration(config)
            }

            if animationTimer == nil {
                animationTimer = Timer.scheduledTimer(withTimeInterval: 0.5, repeats: true) { [weak self] _ in
                    self?.animationFrame += 1
                    self?.updateStatusIcon()
                }
            }
        } else {
            animationTimer?.invalidate()
            animationTimer = nil
            animationFrame = 0

            button.image = NSImage(systemSymbolName: "cloud.fill", accessibilityDescription: "Google Media Backup")
            button.image?.isTemplate = true
        }
    }

    // MARK: - Menu

    private func setupMenu() {
        let menu = NSMenu()

        // Status
        let authStatus = GoogleAuthManager.shared.status
        if authStatus.isReady {
            let statusItem = NSMenuItem(title: "Signed in", action: nil, keyEquivalent: "")
            statusItem.isEnabled = false
            menu.addItem(statusItem)
        } else {
            menu.addItem(NSMenuItem(title: "Sign In...", action: #selector(signIn), keyEquivalent: ""))
        }

        menu.addItem(NSMenuItem.separator())

        // Download section
        if isDownloading {
            menu.addItem(NSMenuItem(title: "Downloading...", action: nil, keyEquivalent: ""))
            menu.addItem(NSMenuItem(title: "Stop Download", action: #selector(stopDownload), keyEquivalent: ""))
        } else {
            menu.addItem(NSMenuItem(title: "Start Download", action: #selector(startDownload), keyEquivalent: "d"))
        }

        menu.addItem(NSMenuItem.separator())

        // Transcription section
        if isTranscribing {
            menu.addItem(NSMenuItem(title: "Transcribing...", action: nil, keyEquivalent: ""))
            menu.addItem(NSMenuItem(title: "Stop Transcription", action: #selector(stopTranscription), keyEquivalent: ""))
        } else {
            let videos = StateManager.shared.getVideosForTranscription()
            let transcribeItem = NSMenuItem(title: "Transcribe Videos (\(videos.count))", action: #selector(startTranscription), keyEquivalent: "t")
            transcribeItem.isEnabled = !videos.isEmpty
            menu.addItem(transcribeItem)
        }

        menu.addItem(NSMenuItem.separator())

        // Open folders
        menu.addItem(NSMenuItem(title: "Open Downloads Folder", action: #selector(openDownloadsFolder), keyEquivalent: ""))
        menu.addItem(NSMenuItem(title: "Show Panel...", action: #selector(showPanel), keyEquivalent: ""))

        menu.addItem(NSMenuItem.separator())

        // Settings
        menu.addItem(NSMenuItem(title: "Preferences...", action: #selector(openConfig), keyEquivalent: ","))

        menu.addItem(NSMenuItem.separator())

        // Quit
        menu.addItem(NSMenuItem(title: "Quit", action: #selector(quitApp), keyEquivalent: "q"))

        statusItem.menu = menu
    }

    // MARK: - Actions

    @objc private func signIn() {
        if !GoogleAuthManager.shared.hasCredentials() {
            GoogleAuthManager.shared.openSetupInstructions()
            return
        }

        progressWindow.show(message: "Opening browser for sign in...")

        GoogleAuthManager.shared.startAuthFlow { [weak self] success, error in
            self?.progressWindow.hide()

            if success {
                showSystemNotification(title: "Sign In Successful", body: "Ready to download from Google Drive and Photos")
                self?.setupMenu()
                self?.mainPanel?.refresh()
            } else {
                let alert = NSAlert()
                alert.messageText = "Sign In Failed"
                alert.informativeText = error ?? "Unknown error occurred"
                alert.alertStyle = .warning
                alert.runModal()
            }
        }
    }

    @objc private func startDownload() {
        guard GoogleAuthManager.shared.status.isReady else {
            signIn()
            return
        }

        progressWindow.show(message: "Starting download...")
        showSystemNotification(title: "Download Started", body: "Scanning Google Drive and Photos...")

        DownloadManager.shared.startDownload { [weak self] downloaded, skipped, errors in
            self?.progressWindow.hide()

            if downloaded > 0 || errors > 0 {
                showSystemNotification(
                    title: "Download Complete",
                    body: "\(downloaded) downloaded, \(skipped) skipped, \(errors) errors"
                )
            }
        }
    }

    @objc private func stopDownload() {
        DownloadManager.shared.stop()
        progressWindow.hide()
        showSystemNotification(title: "Download Stopped", body: "Download has been stopped")
    }

    @objc private func startTranscription() {
        let whisperStatus = TranscriptionManager.shared.checkWhisperStatus()

        guard whisperStatus == .ready else {
            let alert = NSAlert()
            alert.messageText = "Transcription Not Available"

            switch whisperStatus {
            case .notInstalled:
                alert.informativeText = "whisper-cpp is not installed.\n\nInstall with: brew install whisper-cpp"
            case .noModel:
                alert.informativeText = "Whisper model not downloaded.\n\nOpen Preferences to download the model."
            case .ready:
                break
            }

            alert.alertStyle = .warning
            alert.addButton(withTitle: "Open Preferences")
            alert.addButton(withTitle: "Cancel")

            if alert.runModal() == .alertFirstButtonReturn {
                openConfig()
            }
            return
        }

        progressWindow.show(message: "Starting transcription...")
        showSystemNotification(title: "Transcription Started", body: "Processing videos...")

        TranscriptionManager.shared.transcribeAllPending { [weak self] completed, failed in
            self?.progressWindow.hide()

            showSystemNotification(
                title: "Transcription Complete",
                body: "\(completed) transcribed, \(failed) failed"
            )
        }
    }

    @objc private func stopTranscription() {
        TranscriptionManager.shared.stop()
        progressWindow.hide()
        showSystemNotification(title: "Transcription Stopped", body: "Transcription has been stopped")
    }

    @objc private func openDownloadsFolder() {
        let config = ConfigManager.shared.loadConfig()
        try? FileManager.default.createDirectory(atPath: config.downloadPath, withIntermediateDirectories: true)
        NSWorkspace.shared.open(URL(fileURLWithPath: config.downloadPath))
    }

    @objc private func showPanel() {
        mainPanel?.show(near: statusItem)
    }

    @objc private func openConfig() {
        if configWindow == nil {
            configWindow = ConfigWindowController()
            configWindow?.onSave = { [weak self] in
                self?.setupMenu()
                self?.mainPanel?.refresh()
            }
        }
        configWindow?.show()
    }

    @objc private func quitApp() {
        if isDownloading {
            let alert = NSAlert()
            alert.messageText = "Download in Progress"
            alert.informativeText = "Stop download and quit?"
            alert.addButton(withTitle: "Stop and Quit")
            alert.addButton(withTitle: "Cancel")

            if alert.runModal() == .alertFirstButtonReturn {
                DownloadManager.shared.stop()
                NSApp.terminate(nil)
            }
        } else if isTranscribing {
            let alert = NSAlert()
            alert.messageText = "Transcription in Progress"
            alert.informativeText = "Stop transcription and quit?"
            alert.addButton(withTitle: "Stop and Quit")
            alert.addButton(withTitle: "Cancel")

            if alert.runModal() == .alertFirstButtonReturn {
                TranscriptionManager.shared.stop()
                NSApp.terminate(nil)
            }
        } else {
            NSApp.terminate(nil)
        }
    }
}
