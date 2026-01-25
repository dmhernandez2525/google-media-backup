import Cocoa

// MARK: - Progress Window Controller

class ProgressWindowController {
    private var window: NSWindow!
    private var messageLabel: NSTextField!
    private var progressIndicator: NSProgressIndicator!

    init() {
        setupWindow()
    }

    private func setupWindow() {
        window = NSWindow(
            contentRect: NSRect(x: 0, y: 0, width: 300, height: 80),
            styleMask: [.titled, .fullSizeContentView],
            backing: .buffered,
            defer: false
        )
        window.titlebarAppearsTransparent = true
        window.titleVisibility = .hidden
        window.isReleasedWhenClosed = false
        window.level = .floating
        window.backgroundColor = .windowBackgroundColor

        let contentView = window.contentView!

        progressIndicator = NSProgressIndicator(frame: NSRect(x: 20, y: 45, width: 260, height: 20))
        progressIndicator.style = .bar
        progressIndicator.isIndeterminate = true
        contentView.addSubview(progressIndicator)

        messageLabel = NSTextField(labelWithString: "Processing...")
        messageLabel.frame = NSRect(x: 20, y: 15, width: 260, height: 20)
        messageLabel.font = NSFont.systemFont(ofSize: 12)
        messageLabel.textColor = .secondaryLabelColor
        messageLabel.lineBreakMode = .byTruncatingMiddle
        contentView.addSubview(messageLabel)
    }

    func show(message: String) {
        messageLabel.stringValue = message
        progressIndicator.startAnimation(nil)
        window.center()
        window.makeKeyAndOrderFront(nil)
    }

    func update(message: String) {
        messageLabel.stringValue = message
    }

    func hide() {
        progressIndicator.stopAnimation(nil)
        window.orderOut(nil)
    }
}
