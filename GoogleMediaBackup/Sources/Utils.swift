import Foundation

// MARK: - Shell Command Execution

struct ShellResult {
    let output: String
    let exitCode: Int32
    var success: Bool { exitCode == 0 }
}

func runShellCommand(_ command: String, timeout: TimeInterval = 30) -> ShellResult {
    let process = Process()
    let pipe = Pipe()

    process.executableURL = URL(fileURLWithPath: "/bin/zsh")
    process.arguments = ["-c", "export PATH=\"/opt/homebrew/bin:/usr/local/bin:$PATH\"; " + command]
    process.standardOutput = pipe
    process.standardError = pipe

    do {
        try process.run()

        let deadline = Date().addingTimeInterval(timeout)
        while process.isRunning && Date() < deadline {
            Thread.sleep(forTimeInterval: 0.1)
        }

        if process.isRunning {
            process.terminate()
            return ShellResult(output: "Command timed out", exitCode: -1)
        }

        let data = pipe.fileHandleForReading.readDataToEndOfFile()
        let output = String(data: data, encoding: .utf8)?.trimmingCharacters(in: .whitespacesAndNewlines) ?? ""
        return ShellResult(output: output, exitCode: process.terminationStatus)
    } catch {
        return ShellResult(output: error.localizedDescription, exitCode: -1)
    }
}

// MARK: - Logging

class Logger {
    static let shared = Logger()

    private let globalLogPath: String

    private init() {
        let configDir = Paths.configDir
        try? FileManager.default.createDirectory(atPath: configDir, withIntermediateDirectories: true)
        globalLogPath = configDir + "/app.log"
    }

    func log(_ level: LogLevel, _ message: String) {
        let timestamp = ISO8601DateFormatter().string(from: Date())
        let logLine = "[\(timestamp)] [\(level.rawValue)] \(message)\n"

        appendToFile(logLine, path: globalLogPath)

        #if DEBUG
        print("[\(level.rawValue)] \(message)")
        #endif
    }

    private func appendToFile(_ text: String, path: String) {
        if let handle = FileHandle(forWritingAtPath: path) {
            handle.seekToEndOfFile()
            if let data = text.data(using: .utf8) {
                handle.write(data)
            }
            try? handle.close()
        } else {
            try? text.write(toFile: path, atomically: false, encoding: .utf8)
        }
    }

    enum LogLevel: String {
        case info = "INFO"
        case success = "SUCCESS"
        case warning = "WARNING"
        case error = "ERROR"
    }
}

func logInfo(_ message: String) { Logger.shared.log(.info, message) }
func logSuccess(_ message: String) { Logger.shared.log(.success, message) }
func logWarning(_ message: String) { Logger.shared.log(.warning, message) }
func logError(_ message: String) { Logger.shared.log(.error, message) }

// MARK: - Notifications

func showSystemNotification(title: String, body: String) {
    let script = "display notification \"\(body)\" with title \"\(title)\" sound name \"Glass\""
    _ = runShellCommand("osascript -e '\(script)'")
}

// MARK: - Path Utilities

struct Paths {
    static let home = NSHomeDirectory()
    static let downloadBase = home + "/Desktop/Google Media Backup"
    static let configDir = home + "/.config/google-media-backup"
    static let stateDir = configDir + "/state"
    static let driveStatePath = stateDir + "/drive_state.json"
    static let photosStatePath = stateDir + "/photos_state.json"
    static let transcriptionStatePath = stateDir + "/transcription_state.json"
    static let configPath = configDir + "/config.json"
    static let credentialsPath = configDir + "/credentials.json"
    static let tokenPath = configDir + "/token.json"
    static let appLogPath = configDir + "/app.log"
    static let whisperModelsDir = home + "/.cache/whisper"
}

// MARK: - File Size Formatter

func formatFileSize(_ bytes: Int64) -> String {
    let formatter = ByteCountFormatter()
    formatter.countStyle = .file
    return formatter.string(fromByteCount: bytes)
}

// MARK: - Date Formatter

func formatRelativeDate(_ date: Date) -> String {
    let formatter = RelativeDateTimeFormatter()
    formatter.unitsStyle = .full
    return formatter.localizedString(for: date, relativeTo: Date())
}

// MARK: - Array Extension

extension Array {
    subscript(safe index: Int) -> Element? {
        return indices.contains(index) ? self[index] : nil
    }
}
