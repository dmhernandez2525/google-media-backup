import Cocoa

// MARK: - Config Window Controller

class ConfigWindowController: NSObject, NSWindowDelegate {
    private var window: NSWindow!

    // Controls
    private var downloadPathField: NSTextField!
    private var autoDownloadCheckbox: NSButton!
    private var autoTranscribeCheckbox: NSButton!
    private var modelPopup: NSPopUpButton!
    private var downloadVideosCheckbox: NSButton!
    private var downloadDocsCheckbox: NSButton!
    private var downloadPhotosCheckbox: NSButton!

    var onSave: (() -> Void)?

    override init() {
        super.init()
        setupWindow()
    }

    private func setupWindow() {
        window = NSWindow(
            contentRect: NSRect(x: 0, y: 0, width: 500, height: 480),
            styleMask: [.titled, .closable],
            backing: .buffered,
            defer: false
        )
        window.title = "Preferences"
        window.delegate = self
        window.isReleasedWhenClosed = false

        buildUI()
        loadConfig()
    }

    private func buildUI() {
        guard let contentView = window.contentView else { return }
        contentView.wantsLayer = true

        var y: CGFloat = 440

        // Google Account Section
        let accountLabel = NSTextField(labelWithString: "Google Account")
        accountLabel.frame = NSRect(x: 20, y: y, width: 200, height: 20)
        accountLabel.font = NSFont.systemFont(ofSize: 13, weight: .semibold)
        contentView.addSubview(accountLabel)
        y -= 30

        let authStatus = GoogleAuthManager.shared.status
        let statusText = authStatus.isReady ? "Authenticated" : authStatus.displayText
        let statusLabel = NSTextField(labelWithString: "Status: \(statusText)")
        statusLabel.frame = NSRect(x: 20, y: y, width: 300, height: 20)
        statusLabel.font = NSFont.systemFont(ofSize: 12)
        statusLabel.textColor = authStatus.isReady ? .systemGreen : .secondaryLabelColor
        contentView.addSubview(statusLabel)

        let authButton = NSButton(title: authStatus.isReady ? "Sign Out" : "Sign In", target: self, action: #selector(authButtonClicked))
        authButton.frame = NSRect(x: 350, y: y - 3, width: 100, height: 25)
        authButton.bezelStyle = .rounded
        contentView.addSubview(authButton)
        y -= 40

        // Separator
        let sep1 = NSBox(frame: NSRect(x: 20, y: y, width: 460, height: 1))
        sep1.boxType = .separator
        contentView.addSubview(sep1)
        y -= 20

        // Download Location Section
        let downloadLabel = NSTextField(labelWithString: "Download Location")
        downloadLabel.frame = NSRect(x: 20, y: y, width: 200, height: 20)
        downloadLabel.font = NSFont.systemFont(ofSize: 13, weight: .semibold)
        contentView.addSubview(downloadLabel)
        y -= 30

        downloadPathField = NSTextField(frame: NSRect(x: 20, y: y, width: 360, height: 24))
        downloadPathField.isEditable = false
        downloadPathField.stringValue = Paths.downloadBase
        contentView.addSubview(downloadPathField)

        let browseButton = NSButton(title: "Browse...", target: self, action: #selector(browseClicked))
        browseButton.frame = NSRect(x: 390, y: y - 1, width: 80, height: 25)
        browseButton.bezelStyle = .rounded
        contentView.addSubview(browseButton)
        y -= 40

        // Separator
        let sep2 = NSBox(frame: NSRect(x: 20, y: y, width: 460, height: 1))
        sep2.boxType = .separator
        contentView.addSubview(sep2)
        y -= 20

        // Download Options Section
        let optionsLabel = NSTextField(labelWithString: "Download Options")
        optionsLabel.frame = NSRect(x: 20, y: y, width: 200, height: 20)
        optionsLabel.font = NSFont.systemFont(ofSize: 13, weight: .semibold)
        contentView.addSubview(optionsLabel)
        y -= 30

        downloadVideosCheckbox = NSButton(checkboxWithTitle: "Download videos from Google Drive", target: nil, action: nil)
        downloadVideosCheckbox.frame = NSRect(x: 20, y: y, width: 300, height: 20)
        contentView.addSubview(downloadVideosCheckbox)
        y -= 25

        downloadDocsCheckbox = NSButton(checkboxWithTitle: "Download documents from Google Drive", target: nil, action: nil)
        downloadDocsCheckbox.frame = NSRect(x: 20, y: y, width: 300, height: 20)
        contentView.addSubview(downloadDocsCheckbox)
        y -= 25

        downloadPhotosCheckbox = NSButton(checkboxWithTitle: "Download videos from Google Photos", target: nil, action: nil)
        downloadPhotosCheckbox.frame = NSRect(x: 20, y: y, width: 300, height: 20)
        contentView.addSubview(downloadPhotosCheckbox)
        y -= 25

        autoDownloadCheckbox = NSButton(checkboxWithTitle: "Auto-download on app launch", target: nil, action: nil)
        autoDownloadCheckbox.frame = NSRect(x: 20, y: y, width: 300, height: 20)
        contentView.addSubview(autoDownloadCheckbox)
        y -= 40

        // Separator
        let sep3 = NSBox(frame: NSRect(x: 20, y: y, width: 460, height: 1))
        sep3.boxType = .separator
        contentView.addSubview(sep3)
        y -= 20

        // Transcription Section
        let transcriptionLabel = NSTextField(labelWithString: "Transcription")
        transcriptionLabel.frame = NSRect(x: 20, y: y, width: 200, height: 20)
        transcriptionLabel.font = NSFont.systemFont(ofSize: 13, weight: .semibold)
        contentView.addSubview(transcriptionLabel)
        y -= 30

        let whisperStatus = TranscriptionManager.shared.checkWhisperStatus()
        let whisperStatusLabel = NSTextField(labelWithString: "Whisper: \(whisperStatus.displayText)")
        whisperStatusLabel.frame = NSRect(x: 20, y: y, width: 200, height: 20)
        whisperStatusLabel.font = NSFont.systemFont(ofSize: 12)
        whisperStatusLabel.textColor = whisperStatus == .ready ? .systemGreen : .secondaryLabelColor
        contentView.addSubview(whisperStatusLabel)

        if whisperStatus == .notInstalled {
            let installButton = NSButton(title: "Install Whisper", target: self, action: #selector(installWhisperClicked))
            installButton.frame = NSRect(x: 350, y: y - 3, width: 120, height: 25)
            installButton.bezelStyle = .rounded
            contentView.addSubview(installButton)
        }
        y -= 30

        autoTranscribeCheckbox = NSButton(checkboxWithTitle: "Auto-transcribe videos after download", target: nil, action: nil)
        autoTranscribeCheckbox.frame = NSRect(x: 20, y: y, width: 300, height: 20)
        contentView.addSubview(autoTranscribeCheckbox)
        y -= 30

        let modelLabel = NSTextField(labelWithString: "Model:")
        modelLabel.frame = NSRect(x: 20, y: y + 3, width: 50, height: 20)
        modelLabel.font = NSFont.systemFont(ofSize: 12)
        contentView.addSubview(modelLabel)

        modelPopup = NSPopUpButton(frame: NSRect(x: 75, y: y, width: 200, height: 25))
        for model in TranscriptionModel.allCases {
            modelPopup.addItem(withTitle: model.displayName)
        }
        contentView.addSubview(modelPopup)

        let downloadModelButton = NSButton(title: "Download Model", target: self, action: #selector(downloadModelClicked))
        downloadModelButton.frame = NSRect(x: 290, y: y, width: 130, height: 25)
        downloadModelButton.bezelStyle = .rounded
        contentView.addSubview(downloadModelButton)
        y -= 50

        // Buttons
        let cancelButton = NSButton(title: "Cancel", target: self, action: #selector(cancelClicked))
        cancelButton.frame = NSRect(x: 300, y: 20, width: 80, height: 30)
        cancelButton.bezelStyle = .rounded
        cancelButton.keyEquivalent = "\u{1b}" // Escape
        contentView.addSubview(cancelButton)

        let saveButton = NSButton(title: "Save", target: self, action: #selector(saveClicked))
        saveButton.frame = NSRect(x: 390, y: 20, width: 80, height: 30)
        saveButton.bezelStyle = .rounded
        saveButton.keyEquivalent = "\r" // Enter
        contentView.addSubview(saveButton)
    }

    private func loadConfig() {
        let config = ConfigManager.shared.loadConfig()

        downloadPathField.stringValue = config.downloadPath
        autoDownloadCheckbox.state = config.autoDownload ? .on : .off
        autoTranscribeCheckbox.state = config.autoTranscribe ? .on : .off
        downloadVideosCheckbox.state = config.downloadVideos ? .on : .off
        downloadDocsCheckbox.state = config.downloadDocuments ? .on : .off
        downloadPhotosCheckbox.state = config.downloadPhotos ? .on : .off

        // Set model popup
        if let index = TranscriptionModel.allCases.firstIndex(where: { $0.rawValue == config.transcriptionModel }) {
            modelPopup.selectItem(at: index)
        }
    }

    // MARK: - Actions

    @objc private func authButtonClicked() {
        if GoogleAuthManager.shared.status.isReady {
            GoogleAuthManager.shared.logout()
            // Rebuild UI to reflect change
            window.contentView?.subviews.forEach { $0.removeFromSuperview() }
            buildUI()
            loadConfig()
        } else {
            GoogleAuthManager.shared.startAuthFlow { [weak self] success, error in
                if success {
                    showSystemNotification(title: "Sign In Successful", body: "You can now download from Google Drive and Photos")
                    self?.window.contentView?.subviews.forEach { $0.removeFromSuperview() }
                    self?.buildUI()
                    self?.loadConfig()
                } else {
                    let alert = NSAlert()
                    alert.messageText = "Sign In Failed"
                    alert.informativeText = error ?? "Unknown error"
                    alert.alertStyle = .warning
                    alert.runModal()
                }
            }
        }
    }

    @objc private func browseClicked() {
        let panel = NSOpenPanel()
        panel.canChooseFiles = false
        panel.canChooseDirectories = true
        panel.allowsMultipleSelection = false
        panel.prompt = "Select Download Folder"

        if panel.runModal() == .OK, let url = panel.url {
            downloadPathField.stringValue = url.path
        }
    }

    @objc private func installWhisperClicked() {
        let alert = NSAlert()
        alert.messageText = "Install Whisper"
        alert.informativeText = "This will install whisper-cpp using Homebrew.\n\nCommand: brew install whisper-cpp"
        alert.addButton(withTitle: "Install")
        alert.addButton(withTitle: "Cancel")

        if alert.runModal() == .alertFirstButtonReturn {
            let result = runShellCommand("brew install whisper-cpp 2>&1", timeout: 300)
            if result.success {
                showSystemNotification(title: "Installation Complete", body: "whisper-cpp installed successfully")
                // Rebuild UI
                window.contentView?.subviews.forEach { $0.removeFromSuperview() }
                buildUI()
                loadConfig()
            } else {
                let errorAlert = NSAlert()
                errorAlert.messageText = "Installation Failed"
                errorAlert.informativeText = result.output
                errorAlert.alertStyle = .warning
                errorAlert.runModal()
            }
        }
    }

    @objc private func downloadModelClicked() {
        let selectedIndex = modelPopup.indexOfSelectedItem
        guard let model = TranscriptionModel.allCases[safe: selectedIndex] else { return }

        let alert = NSAlert()
        alert.messageText = "Download Model"
        alert.informativeText = "Download the \(model.displayName) model?\n\nThis may take a while depending on your internet connection."
        alert.addButton(withTitle: "Download")
        alert.addButton(withTitle: "Cancel")

        if alert.runModal() == .alertFirstButtonReturn {
            let progressWindow = ProgressWindowController()
            progressWindow.show(message: "Downloading \(model.rawValue) model...")

            TranscriptionManager.shared.downloadModel(model, progress: { msg in
                progressWindow.update(message: msg)
            }) { success in
                progressWindow.hide()
                if success {
                    showSystemNotification(title: "Download Complete", body: "\(model.rawValue) model ready")
                } else {
                    let errorAlert = NSAlert()
                    errorAlert.messageText = "Download Failed"
                    errorAlert.informativeText = "Failed to download the model. Please try again."
                    errorAlert.alertStyle = .warning
                    errorAlert.runModal()
                }
            }
        }
    }

    @objc private func cancelClicked() {
        window.orderOut(nil)
    }

    @objc private func saveClicked() {
        var config = ConfigManager.shared.loadConfig()

        config.downloadPath = downloadPathField.stringValue
        config.autoDownload = autoDownloadCheckbox.state == .on
        config.autoTranscribe = autoTranscribeCheckbox.state == .on
        config.downloadVideos = downloadVideosCheckbox.state == .on
        config.downloadDocuments = downloadDocsCheckbox.state == .on
        config.downloadPhotos = downloadPhotosCheckbox.state == .on

        if let model = TranscriptionModel.allCases[safe: modelPopup.indexOfSelectedItem] {
            config.transcriptionModel = model.rawValue
        }

        if ConfigManager.shared.saveConfig(config) {
            onSave?()
            window.orderOut(nil)
        }
    }

    // MARK: - Show

    func show() {
        window.contentView?.subviews.forEach { $0.removeFromSuperview() }
        buildUI()
        loadConfig()
        window.center()
        window.makeKeyAndOrderFront(nil)
        NSApp.activate(ignoringOtherApps: true)
    }
}
