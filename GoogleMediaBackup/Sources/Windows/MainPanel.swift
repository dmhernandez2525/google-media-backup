import Cocoa

// MARK: - Google-Style Colors

struct GoogleColors {
    static let blue = NSColor(red: 0.10, green: 0.45, blue: 0.91, alpha: 1.0)
    static let blueLight = NSColor(red: 0.91, green: 0.94, blue: 0.99, alpha: 1.0)
    static let blueHover = NSColor(red: 0.08, green: 0.34, blue: 0.69, alpha: 1.0)
    static let green = NSColor(red: 0.20, green: 0.66, blue: 0.33, alpha: 1.0)
    static let yellow = NSColor(red: 0.98, green: 0.74, blue: 0.02, alpha: 1.0)
    static let yellowBg = NSColor(red: 1.0, green: 0.97, blue: 0.88, alpha: 1.0)
    static let red = NSColor(red: 0.92, green: 0.26, blue: 0.21, alpha: 1.0)
    static let textPrimary = NSColor(red: 0.13, green: 0.13, blue: 0.14, alpha: 1.0)
    static let textSecondary = NSColor(red: 0.37, green: 0.38, blue: 0.41, alpha: 1.0)
    static let textTertiary = NSColor(red: 0.50, green: 0.53, blue: 0.55, alpha: 1.0)
    static let border = NSColor(red: 0.85, green: 0.87, blue: 0.88, alpha: 1.0)
    static let bgSecondary = NSColor(red: 0.95, green: 0.96, blue: 0.96, alpha: 1.0)
    static let bgHover = NSColor(red: 0.91, green: 0.92, blue: 0.93, alpha: 1.0)
}

// MARK: - Navigation Item

enum NavigationItem: String, CaseIterable {
    case home = "Home"
    case downloads = "Downloads"
    case transcriptions = "Transcriptions"

    var icon: String {
        switch self {
        case .home: return "house.fill"
        case .downloads: return "arrow.down.circle.fill"
        case .transcriptions: return "waveform"
        }
    }
}

// MARK: - Main Panel Controller

class MainPanelController: NSObject, NSWindowDelegate {
    private var window: NSPanel!
    private var contentContainer: NSView!
    private var sidebarView: NSView!
    private var headerView: NSView!

    private var selectedNav: NavigationItem = .home
    private var navButtons: [NavigationItem: NSButton] = [:]

    // Header buttons
    private var pauseButton: NSButton!
    private var settingsButton: NSButton!

    // State
    private var isPaused = false

    // Callbacks
    var onStartDownload: (() -> Void)?
    var onStopDownload: (() -> Void)?
    var onStartTranscription: (() -> Void)?
    var onOpenDownloads: (() -> Void)?
    var onOpenConfig: (() -> Void)?
    var onSignIn: (() -> Void)?

    override init() {
        super.init()
        setupWindow()
    }

    private func setupWindow() {
        window = NSPanel(
            contentRect: NSRect(x: 0, y: 0, width: 720, height: 560),
            styleMask: [.titled, .closable, .resizable, .fullSizeContentView],
            backing: .buffered,
            defer: false
        )
        window.title = "Google Media Backup"
        window.titlebarAppearsTransparent = true
        window.titleVisibility = .hidden
        window.delegate = self
        window.isReleasedWhenClosed = false
        window.level = .floating
        window.collectionBehavior = [.canJoinAllSpaces, .transient]
        window.backgroundColor = .white
        window.minSize = NSSize(width: 600, height: 400)
        window.isMovableByWindowBackground = true

        let mainView = NSView(frame: window.contentView!.bounds)
        mainView.wantsLayer = true
        mainView.layer?.backgroundColor = NSColor.white.cgColor
        window.contentView = mainView

        buildLayout(in: mainView)
    }

    private func buildLayout(in container: NSView) {
        container.subviews.forEach { $0.removeFromSuperview() }

        let bounds = container.bounds

        // Header
        headerView = buildHeader()
        headerView.frame = NSRect(x: 0, y: bounds.height - 56, width: bounds.width, height: 56)
        headerView.autoresizingMask = [.width, .minYMargin]
        container.addSubview(headerView)

        // Sidebar
        sidebarView = buildSidebar()
        sidebarView.frame = NSRect(x: 0, y: 0, width: 200, height: bounds.height - 56)
        sidebarView.autoresizingMask = [.height]
        container.addSubview(sidebarView)

        // Content
        contentContainer = NSView(frame: NSRect(x: 200, y: 0, width: bounds.width - 200, height: bounds.height - 56))
        contentContainer.wantsLayer = true
        contentContainer.autoresizingMask = [.width, .height]
        container.addSubview(contentContainer)

        showScreen(selectedNav)
    }

    // MARK: - Header

    private func buildHeader() -> NSView {
        let header = NSView(frame: NSRect(x: 0, y: 0, width: 720, height: 56))
        header.wantsLayer = true
        header.layer?.backgroundColor = NSColor.white.cgColor

        // Bottom border
        let border = NSView(frame: NSRect(x: 0, y: 0, width: 720, height: 1))
        border.wantsLayer = true
        border.layer?.backgroundColor = GoogleColors.border.cgColor
        border.autoresizingMask = [.width]
        header.addSubview(border)

        // App icon
        let appIcon = NSImageView(frame: NSRect(x: 20, y: 14, width: 28, height: 28))
        if let img = NSImage(systemSymbolName: "cloud.fill", accessibilityDescription: nil) {
            let config = NSImage.SymbolConfiguration(pointSize: 24, weight: .regular)
                .applying(NSImage.SymbolConfiguration(paletteColors: [GoogleColors.blue]))
            appIcon.image = img.withSymbolConfiguration(config)
        }
        header.addSubview(appIcon)

        // App title
        let title = NSTextField(labelWithString: "Google Media Backup")
        title.frame = NSRect(x: 54, y: 18, width: 180, height: 20)
        title.font = NSFont.systemFont(ofSize: 16, weight: .semibold)
        title.textColor = GoogleColors.textPrimary
        header.addSubview(title)

        // Right side buttons
        var rightX: CGFloat = 680

        settingsButton = createIconButton(icon: "gearshape.fill", action: #selector(settingsClicked))
        settingsButton.frame = NSRect(x: rightX - 32, y: 12, width: 32, height: 32)
        settingsButton.autoresizingMask = [.minXMargin]
        header.addSubview(settingsButton)
        rightX -= 40

        pauseButton = createIconButton(icon: isPaused ? "play.circle" : "pause.circle", action: #selector(pauseClicked))
        pauseButton.frame = NSRect(x: rightX - 32, y: 12, width: 32, height: 32)
        pauseButton.autoresizingMask = [.minXMargin]
        pauseButton.toolTip = isPaused ? "Resume" : "Pause"
        header.addSubview(pauseButton)

        return header
    }

    private func createIconButton(icon: String, action: Selector) -> NSButton {
        let btn = NSButton(frame: NSRect(x: 0, y: 0, width: 32, height: 32))
        btn.bezelStyle = .regularSquare
        btn.isBordered = false
        btn.target = self
        btn.action = action

        if let img = NSImage(systemSymbolName: icon, accessibilityDescription: nil) {
            let config = NSImage.SymbolConfiguration(pointSize: 16, weight: .regular)
                .applying(NSImage.SymbolConfiguration(paletteColors: [GoogleColors.textSecondary]))
            btn.image = img.withSymbolConfiguration(config)
        }

        return btn
    }

    // MARK: - Sidebar

    private func buildSidebar() -> NSView {
        let sidebar = NSView(frame: NSRect(x: 0, y: 0, width: 200, height: 500))
        sidebar.wantsLayer = true
        sidebar.layer?.backgroundColor = NSColor.white.cgColor

        var y = sidebar.frame.height - 20

        // Open Downloads button
        let openBtn = NSButton(frame: NSRect(x: 10, y: y - 36, width: 180, height: 36))
        openBtn.title = "  Open Downloads"
        openBtn.bezelStyle = .rounded
        openBtn.target = self
        openBtn.action = #selector(openDownloadsClicked)
        openBtn.font = NSFont.systemFont(ofSize: 13, weight: .medium)

        if let img = NSImage(systemSymbolName: "folder.fill", accessibilityDescription: nil) {
            let config = NSImage.SymbolConfiguration(pointSize: 14, weight: .regular)
                .applying(NSImage.SymbolConfiguration(paletteColors: [GoogleColors.textSecondary]))
            openBtn.image = img.withSymbolConfiguration(config)
            openBtn.imagePosition = .imageLeft
        }

        sidebar.addSubview(openBtn)
        y -= 56

        // Navigation items
        navButtons.removeAll()

        for item in NavigationItem.allCases {
            let navBtn = createNavButton(item: item)
            navBtn.frame = NSRect(x: 10, y: y - 36, width: 180, height: 36)
            sidebar.addSubview(navBtn)
            navButtons[item] = navBtn
            y -= 40
        }

        updateNavSelection()

        return sidebar
    }

    private func createNavButton(item: NavigationItem) -> NSButton {
        let btn = NSButton(frame: NSRect(x: 0, y: 0, width: 180, height: 36))
        btn.title = "  \(item.rawValue)"
        btn.bezelStyle = .regularSquare
        btn.isBordered = false
        btn.target = self
        btn.action = #selector(navItemClicked(_:))
        btn.font = NSFont.systemFont(ofSize: 13, weight: .medium)
        btn.alignment = .left
        btn.tag = NavigationItem.allCases.firstIndex(of: item) ?? 0

        btn.wantsLayer = true
        btn.layer?.cornerRadius = 18

        if let img = NSImage(systemSymbolName: item.icon, accessibilityDescription: nil) {
            let config = NSImage.SymbolConfiguration(pointSize: 14, weight: .regular)
            btn.image = img.withSymbolConfiguration(config)
            btn.imagePosition = .imageLeft
        }

        return btn
    }

    private func updateNavSelection() {
        for (item, btn) in navButtons {
            let isSelected = item == selectedNav

            if isSelected {
                btn.layer?.backgroundColor = GoogleColors.blueLight.cgColor
                btn.contentTintColor = GoogleColors.blue

                if let img = NSImage(systemSymbolName: item.icon, accessibilityDescription: nil) {
                    let config = NSImage.SymbolConfiguration(pointSize: 14, weight: .regular)
                        .applying(NSImage.SymbolConfiguration(paletteColors: [GoogleColors.blue]))
                    btn.image = img.withSymbolConfiguration(config)
                }

                let attrStr = NSMutableAttributedString(string: "  \(item.rawValue)")
                attrStr.addAttributes([
                    .foregroundColor: GoogleColors.blue,
                    .font: NSFont.systemFont(ofSize: 13, weight: .medium)
                ], range: NSRange(location: 0, length: attrStr.length))
                btn.attributedTitle = attrStr
            } else {
                btn.layer?.backgroundColor = NSColor.clear.cgColor
                btn.contentTintColor = GoogleColors.textSecondary

                if let img = NSImage(systemSymbolName: item.icon, accessibilityDescription: nil) {
                    let config = NSImage.SymbolConfiguration(pointSize: 14, weight: .regular)
                        .applying(NSImage.SymbolConfiguration(paletteColors: [GoogleColors.textSecondary]))
                    btn.image = img.withSymbolConfiguration(config)
                }

                let attrStr = NSMutableAttributedString(string: "  \(item.rawValue)")
                attrStr.addAttributes([
                    .foregroundColor: GoogleColors.textSecondary,
                    .font: NSFont.systemFont(ofSize: 13, weight: .medium)
                ], range: NSRange(location: 0, length: attrStr.length))
                btn.attributedTitle = attrStr
            }
        }
    }

    // MARK: - Screens

    private func showScreen(_ screen: NavigationItem) {
        contentContainer.subviews.forEach { $0.removeFromSuperview() }

        switch screen {
        case .home:
            buildHomeScreen()
        case .downloads:
            buildDownloadsScreen()
        case .transcriptions:
            buildTranscriptionsScreen()
        }
    }

    private func buildHomeScreen() {
        let bounds = contentContainer.bounds
        var y = bounds.height - 30

        // Auth status check
        let authStatus = GoogleAuthManager.shared.status
        if !authStatus.isReady {
            let authCard = buildAuthCard(width: bounds.width - 40)
            authCard.frame = NSRect(x: 20, y: y - 120, width: bounds.width - 40, height: 110)
            contentContainer.addSubview(authCard)
            y -= 140
        }

        // Status header
        let (statusView, statusHeight) = buildStatusHeader(width: bounds.width - 40)
        statusView.frame = NSRect(x: 20, y: y - statusHeight, width: bounds.width - 40, height: statusHeight)
        contentContainer.addSubview(statusView)
        y -= statusHeight + 20

        // Statistics cards
        let stats = DownloadManager.shared.getStatistics()

        let cardsContainer = NSView(frame: NSRect(x: 20, y: y - 80, width: bounds.width - 40, height: 70))
        cardsContainer.wantsLayer = true

        let cardWidth = (bounds.width - 60) / 3

        let downloadedCard = buildStatCard(title: "Downloaded", value: "\(stats.downloaded)", icon: "checkmark.circle.fill", color: GoogleColors.green)
        downloadedCard.frame = NSRect(x: 0, y: 0, width: cardWidth - 10, height: 70)
        cardsContainer.addSubview(downloadedCard)

        let pendingCard = buildStatCard(title: "Pending", value: "\(stats.pending)", icon: "clock.fill", color: GoogleColors.textTertiary)
        pendingCard.frame = NSRect(x: cardWidth, y: 0, width: cardWidth - 10, height: 70)
        cardsContainer.addSubview(pendingCard)

        let transcribeCard = buildStatCard(title: "To Transcribe", value: "\(stats.videosToTranscribe)", icon: "waveform", color: GoogleColors.blue)
        transcribeCard.frame = NSRect(x: cardWidth * 2, y: 0, width: cardWidth - 10, height: 70)
        cardsContainer.addSubview(transcribeCard)

        contentContainer.addSubview(cardsContainer)
        y -= 100

        // Action buttons
        let actionsContainer = NSView(frame: NSRect(x: 20, y: y - 50, width: bounds.width - 40, height: 40))

        let downloadStatus = DownloadManager.shared.status
        let downloadBtn: NSButton
        if downloadStatus.isActive {
            downloadBtn = NSButton(title: "Stop Download", target: self, action: #selector(stopDownloadClicked))
        } else {
            downloadBtn = NSButton(title: "Start Download", target: self, action: #selector(startDownloadClicked))
        }
        downloadBtn.frame = NSRect(x: 0, y: 5, width: 140, height: 30)
        downloadBtn.bezelStyle = .rounded
        actionsContainer.addSubview(downloadBtn)

        let transcribeBtn = NSButton(title: "Transcribe Videos", target: self, action: #selector(startTranscriptionClicked))
        transcribeBtn.frame = NSRect(x: 150, y: 5, width: 140, height: 30)
        transcribeBtn.bezelStyle = .rounded
        transcribeBtn.isEnabled = stats.videosToTranscribe > 0
        actionsContainer.addSubview(transcribeBtn)

        contentContainer.addSubview(actionsContainer)
        y -= 70

        // Quick links
        let quickLinksLabel = NSTextField(labelWithString: "Quick links")
        quickLinksLabel.frame = NSRect(x: 20, y: y - 20, width: 200, height: 20)
        quickLinksLabel.font = NSFont.systemFont(ofSize: 11, weight: .medium)
        quickLinksLabel.textColor = GoogleColors.textSecondary
        contentContainer.addSubview(quickLinksLabel)
        y -= 35

        let quickLinks: [(title: String, icon: String, action: Selector)] = [
            ("Open Google Drive", "arrow.up.right", #selector(openDriveWebClicked)),
            ("Open Google Photos", "arrow.up.right", #selector(openPhotosWebClicked)),
            ("Preferences", "gearshape", #selector(settingsClicked))
        ]

        for link in quickLinks {
            let btn = buildQuickLinkButton(title: link.title, icon: link.icon, action: link.action)
            btn.frame = NSRect(x: 20, y: y - 35, width: 250, height: 30)
            contentContainer.addSubview(btn)
            y -= 38
        }
    }

    private func buildAuthCard(width: CGFloat) -> NSView {
        let card = NSView(frame: NSRect(x: 0, y: 0, width: width, height: 110))
        card.wantsLayer = true
        card.layer?.backgroundColor = GoogleColors.yellowBg.cgColor
        card.layer?.cornerRadius = 12

        let icon = NSImageView(frame: NSRect(x: 20, y: 55, width: 32, height: 32))
        if let img = NSImage(systemSymbolName: "exclamationmark.triangle.fill", accessibilityDescription: nil) {
            let config = NSImage.SymbolConfiguration(pointSize: 24, weight: .regular)
                .applying(NSImage.SymbolConfiguration(paletteColors: [GoogleColors.yellow]))
            icon.image = img.withSymbolConfiguration(config)
        }
        card.addSubview(icon)

        let titleLabel = NSTextField(labelWithString: "Sign in required")
        titleLabel.frame = NSRect(x: 60, y: 70, width: width - 80, height: 20)
        titleLabel.font = NSFont.systemFont(ofSize: 14, weight: .semibold)
        titleLabel.textColor = GoogleColors.textPrimary
        card.addSubview(titleLabel)

        let descLabel = NSTextField(labelWithString: "Sign in with your Google account to download files from Google Drive and Photos.")
        descLabel.frame = NSRect(x: 60, y: 45, width: width - 80, height: 20)
        descLabel.font = NSFont.systemFont(ofSize: 12)
        descLabel.textColor = GoogleColors.textSecondary
        card.addSubview(descLabel)

        let signInBtn = NSButton(title: "Sign In", target: self, action: #selector(signInClicked))
        signInBtn.frame = NSRect(x: 60, y: 10, width: 100, height: 28)
        signInBtn.bezelStyle = .rounded
        card.addSubview(signInBtn)

        let setupBtn = NSButton(title: "Setup Instructions", target: self, action: #selector(setupInstructionsClicked))
        setupBtn.frame = NSRect(x: 170, y: 10, width: 140, height: 28)
        setupBtn.bezelStyle = .rounded
        card.addSubview(setupBtn)

        return card
    }

    private func buildStatusHeader(width: CGFloat) -> (NSView, CGFloat) {
        let container = NSView(frame: NSRect(x: 0, y: 0, width: width, height: 60))

        let downloadStatus = DownloadManager.shared.status

        // Status icon
        let iconView = NSImageView(frame: NSRect(x: 0, y: 20, width: 32, height: 32))
        let iconName: String
        let iconColor: NSColor

        switch downloadStatus {
        case .idle:
            iconName = "checkmark.circle.fill"
            iconColor = GoogleColors.green
        case .scanning, .downloading:
            iconName = "arrow.down.circle.fill"
            iconColor = GoogleColors.blue
        case .paused:
            iconName = "pause.circle.fill"
            iconColor = GoogleColors.textTertiary
        case .completed:
            iconName = "checkmark.circle.fill"
            iconColor = GoogleColors.green
        case .error:
            iconName = "exclamationmark.circle.fill"
            iconColor = GoogleColors.red
        }

        if let img = NSImage(systemSymbolName: iconName, accessibilityDescription: nil) {
            let config = NSImage.SymbolConfiguration(pointSize: 28, weight: .regular)
                .applying(NSImage.SymbolConfiguration(paletteColors: [iconColor]))
            iconView.image = img.withSymbolConfiguration(config)
        }
        container.addSubview(iconView)

        // Status text
        let statusLabel = NSTextField(labelWithString: downloadStatus.displayText)
        statusLabel.frame = NSRect(x: 42, y: 30, width: width - 50, height: 24)
        statusLabel.font = NSFont.systemFont(ofSize: 22, weight: .regular)
        statusLabel.textColor = GoogleColors.textPrimary
        container.addSubview(statusLabel)

        // Subtitle
        let stats = DownloadManager.shared.getStatistics()
        let subtitleLabel = NSTextField(labelWithString: "\(stats.total) files tracked")
        subtitleLabel.frame = NSRect(x: 42, y: 10, width: width - 50, height: 16)
        subtitleLabel.font = NSFont.systemFont(ofSize: 12)
        subtitleLabel.textColor = GoogleColors.textSecondary
        container.addSubview(subtitleLabel)

        return (container, 60)
    }

    private func buildStatCard(title: String, value: String, icon: String, color: NSColor) -> NSView {
        let card = NSView(frame: NSRect(x: 0, y: 0, width: 150, height: 70))
        card.wantsLayer = true
        card.layer?.backgroundColor = GoogleColors.bgSecondary.cgColor
        card.layer?.cornerRadius = 8

        let iconView = NSImageView(frame: NSRect(x: 12, y: 38, width: 20, height: 20))
        if let img = NSImage(systemSymbolName: icon, accessibilityDescription: nil) {
            let config = NSImage.SymbolConfiguration(pointSize: 16, weight: .regular)
                .applying(NSImage.SymbolConfiguration(paletteColors: [color]))
            iconView.image = img.withSymbolConfiguration(config)
        }
        card.addSubview(iconView)

        let valueLabel = NSTextField(labelWithString: value)
        valueLabel.frame = NSRect(x: 40, y: 35, width: 100, height: 24)
        valueLabel.font = NSFont.systemFont(ofSize: 20, weight: .semibold)
        valueLabel.textColor = GoogleColors.textPrimary
        card.addSubview(valueLabel)

        let titleLabel = NSTextField(labelWithString: title)
        titleLabel.frame = NSRect(x: 12, y: 10, width: 130, height: 16)
        titleLabel.font = NSFont.systemFont(ofSize: 12)
        titleLabel.textColor = GoogleColors.textSecondary
        card.addSubview(titleLabel)

        return card
    }

    private func buildQuickLinkButton(title: String, icon: String, action: Selector) -> NSButton {
        let btn = NSButton(frame: NSRect(x: 0, y: 0, width: 250, height: 30))
        btn.title = "  \(title)"
        btn.bezelStyle = .rounded
        btn.target = self
        btn.action = action
        btn.font = NSFont.systemFont(ofSize: 13, weight: .regular)
        btn.alignment = .left

        if let img = NSImage(systemSymbolName: icon, accessibilityDescription: nil) {
            let config = NSImage.SymbolConfiguration(pointSize: 14, weight: .regular)
                .applying(NSImage.SymbolConfiguration(paletteColors: [GoogleColors.textSecondary]))
            btn.image = img.withSymbolConfiguration(config)
            btn.imagePosition = .imageLeft
        }

        return btn
    }

    private func buildDownloadsScreen() {
        let bounds = contentContainer.bounds
        var y = bounds.height - 30

        let titleLabel = NSTextField(labelWithString: "Downloads")
        titleLabel.frame = NSRect(x: 20, y: y - 28, width: 200, height: 28)
        titleLabel.font = NSFont.systemFont(ofSize: 22, weight: .regular)
        titleLabel.textColor = GoogleColors.textPrimary
        contentContainer.addSubview(titleLabel)
        y -= 50

        let files = StateManager.shared.getAllFiles()

        if files.isEmpty {
            let emptyLabel = NSTextField(labelWithString: "No files downloaded yet. Click 'Start Download' to begin.")
            emptyLabel.frame = NSRect(x: 20, y: y - 20, width: bounds.width - 40, height: 20)
            emptyLabel.font = NSFont.systemFont(ofSize: 13)
            emptyLabel.textColor = GoogleColors.textSecondary
            contentContainer.addSubview(emptyLabel)
        } else {
            // Scroll view for files
            let scrollView = NSScrollView(frame: NSRect(x: 20, y: 20, width: bounds.width - 40, height: y - 20))
            scrollView.hasVerticalScroller = true
            scrollView.borderType = .noBorder
            scrollView.autoresizingMask = [.width, .height]

            let clipView = NSClipView()
            let contentHeight = CGFloat(files.count) * 50
            clipView.documentView = NSView(frame: NSRect(x: 0, y: 0, width: bounds.width - 60, height: max(contentHeight, y - 20)))
            scrollView.contentView = clipView

            var fileY = contentHeight
            for file in files.prefix(100) {
                fileY -= 50
                let row = buildFileRow(file: file, width: bounds.width - 60)
                row.frame = NSRect(x: 0, y: fileY, width: bounds.width - 60, height: 50)
                clipView.documentView?.addSubview(row)
            }

            contentContainer.addSubview(scrollView)
        }
    }

    private func buildFileRow(file: FileState, width: CGFloat) -> NSView {
        let row = NSView(frame: NSRect(x: 0, y: 0, width: width, height: 50))
        row.wantsLayer = true

        // File icon
        let iconView = NSImageView(frame: NSRect(x: 0, y: 13, width: 24, height: 24))
        let iconName = file.isVideo ? "film" : "doc"
        if let img = NSImage(systemSymbolName: iconName, accessibilityDescription: nil) {
            let config = NSImage.SymbolConfiguration(pointSize: 18, weight: .regular)
                .applying(NSImage.SymbolConfiguration(paletteColors: [GoogleColors.textSecondary]))
            iconView.image = img.withSymbolConfiguration(config)
        }
        row.addSubview(iconView)

        // Filename
        let nameLabel = NSTextField(labelWithString: file.name)
        nameLabel.frame = NSRect(x: 34, y: 26, width: width - 150, height: 18)
        nameLabel.font = NSFont.systemFont(ofSize: 13, weight: .regular)
        nameLabel.textColor = GoogleColors.textPrimary
        nameLabel.lineBreakMode = .byTruncatingMiddle
        row.addSubview(nameLabel)

        // Status
        let statusText = "\(formatFileSize(file.size)), \(file.downloadStatus.rawValue)"
        let statusLabel = NSTextField(labelWithString: statusText)
        statusLabel.frame = NSRect(x: 34, y: 6, width: width - 150, height: 16)
        statusLabel.font = NSFont.systemFont(ofSize: 12)
        statusLabel.textColor = GoogleColors.textSecondary
        row.addSubview(statusLabel)

        // Status icon
        let statusIcon = NSImageView(frame: NSRect(x: width - 30, y: 13, width: 24, height: 24))
        let statusIconName: String
        let statusColor: NSColor

        switch file.downloadStatus {
        case .complete:
            statusIconName = "checkmark.circle.fill"
            statusColor = GoogleColors.green
        case .downloading:
            statusIconName = "arrow.down.circle.fill"
            statusColor = GoogleColors.blue
        case .pending:
            statusIconName = "clock.fill"
            statusColor = GoogleColors.textTertiary
        case .error:
            statusIconName = "exclamationmark.circle.fill"
            statusColor = GoogleColors.red
        }

        if let img = NSImage(systemSymbolName: statusIconName, accessibilityDescription: nil) {
            let config = NSImage.SymbolConfiguration(pointSize: 18, weight: .regular)
                .applying(NSImage.SymbolConfiguration(paletteColors: [statusColor]))
            statusIcon.image = img.withSymbolConfiguration(config)
        }
        row.addSubview(statusIcon)

        return row
    }

    private func buildTranscriptionsScreen() {
        let bounds = contentContainer.bounds
        var y = bounds.height - 30

        let titleLabel = NSTextField(labelWithString: "Transcriptions")
        titleLabel.frame = NSRect(x: 20, y: y - 28, width: 200, height: 28)
        titleLabel.font = NSFont.systemFont(ofSize: 22, weight: .regular)
        titleLabel.textColor = GoogleColors.textPrimary
        contentContainer.addSubview(titleLabel)
        y -= 50

        // Whisper status
        let whisperStatus = TranscriptionManager.shared.checkWhisperStatus()
        let statusLabel = NSTextField(labelWithString: "Whisper: \(whisperStatus.displayText)")
        statusLabel.frame = NSRect(x: 20, y: y - 20, width: 200, height: 20)
        statusLabel.font = NSFont.systemFont(ofSize: 13)
        statusLabel.textColor = whisperStatus == .ready ? GoogleColors.green : GoogleColors.textSecondary
        contentContainer.addSubview(statusLabel)
        y -= 40

        // Transcription status
        let transStatus = TranscriptionManager.shared.status
        let transStatusLabel = NSTextField(labelWithString: transStatus.displayText)
        transStatusLabel.frame = NSRect(x: 20, y: y - 20, width: bounds.width - 40, height: 20)
        transStatusLabel.font = NSFont.systemFont(ofSize: 13)
        transStatusLabel.textColor = GoogleColors.textPrimary
        contentContainer.addSubview(transStatusLabel)
        y -= 40

        // Videos to transcribe
        let videos = StateManager.shared.getVideosForTranscription()

        let pendingLabel = NSTextField(labelWithString: "\(videos.count) videos pending transcription")
        pendingLabel.frame = NSRect(x: 20, y: y - 20, width: bounds.width - 40, height: 20)
        pendingLabel.font = NSFont.systemFont(ofSize: 13)
        pendingLabel.textColor = GoogleColors.textSecondary
        contentContainer.addSubview(pendingLabel)
        y -= 40

        // Transcribe button
        let transcribeBtn = NSButton(title: "Transcribe All", target: self, action: #selector(startTranscriptionClicked))
        transcribeBtn.frame = NSRect(x: 20, y: y - 30, width: 140, height: 30)
        transcribeBtn.bezelStyle = .rounded
        transcribeBtn.isEnabled = !videos.isEmpty && whisperStatus == .ready
        contentContainer.addSubview(transcribeBtn)
    }

    // MARK: - Actions

    @objc private func navItemClicked(_ sender: NSButton) {
        guard let item = NavigationItem.allCases[safe: sender.tag] else { return }
        selectedNav = item
        updateNavSelection()
        showScreen(item)
    }

    @objc private func openDownloadsClicked() {
        onOpenDownloads?()
    }

    @objc private func pauseClicked() {
        isPaused = !isPaused

        if isPaused {
            DownloadManager.shared.pause()
        } else {
            DownloadManager.shared.resume()
        }

        let iconName = isPaused ? "play.circle" : "pause.circle"
        if let img = NSImage(systemSymbolName: iconName, accessibilityDescription: nil) {
            let config = NSImage.SymbolConfiguration(pointSize: 16, weight: .regular)
                .applying(NSImage.SymbolConfiguration(paletteColors: [GoogleColors.textSecondary]))
            pauseButton.image = img.withSymbolConfiguration(config)
        }
        pauseButton.toolTip = isPaused ? "Resume" : "Pause"
    }

    @objc private func settingsClicked() {
        onOpenConfig?()
    }

    @objc private func signInClicked() {
        onSignIn?()
    }

    @objc private func setupInstructionsClicked() {
        GoogleAuthManager.shared.openSetupInstructions()
    }

    @objc private func startDownloadClicked() {
        onStartDownload?()
    }

    @objc private func stopDownloadClicked() {
        onStopDownload?()
    }

    @objc private func startTranscriptionClicked() {
        onStartTranscription?()
    }

    @objc private func openDriveWebClicked() {
        if let url = URL(string: "https://drive.google.com") {
            NSWorkspace.shared.open(url)
        }
    }

    @objc private func openPhotosWebClicked() {
        if let url = URL(string: "https://photos.google.com") {
            NSWorkspace.shared.open(url)
        }
    }

    // MARK: - Public Methods

    func show(near statusItem: NSStatusItem) {
        buildLayout(in: window.contentView!)

        if let button = statusItem.button, let buttonWindow = button.window {
            let buttonFrame = button.convert(button.bounds, to: nil)
            let screenFrame = buttonWindow.convertToScreen(buttonFrame)
            let windowFrame = window.frame

            var x = screenFrame.midX - windowFrame.width / 2
            let y = screenFrame.minY - windowFrame.height - 5

            if let screen = NSScreen.main {
                let screenRight = screen.visibleFrame.maxX
                if x + windowFrame.width > screenRight {
                    x = screenRight - windowFrame.width - 10
                }
                if x < screen.visibleFrame.minX {
                    x = screen.visibleFrame.minX + 10
                }
            }

            window.setFrameOrigin(NSPoint(x: x, y: y))
        } else {
            window.center()
        }

        window.makeKeyAndOrderFront(nil)
        NSApp.activate(ignoringOtherApps: true)
    }

    func hide() {
        window.orderOut(nil)
    }

    func refresh() {
        if window.isVisible {
            showScreen(selectedNav)
        }
    }
}
