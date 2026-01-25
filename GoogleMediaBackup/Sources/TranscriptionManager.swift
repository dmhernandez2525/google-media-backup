import Cocoa

// MARK: - Transcription Configuration

struct TranscriptionConfig: Codable {
    var enabled: Bool
    var model: String
    var outputFormat: String
    var language: String

    enum CodingKeys: String, CodingKey {
        case enabled
        case model
        case outputFormat = "output_format"
        case language
    }

    static var `default`: TranscriptionConfig {
        TranscriptionConfig(
            enabled: true,
            model: "small",
            outputFormat: "txt",
            language: "en"
        )
    }
}

// MARK: - Transcription Model

enum TranscriptionModel: String, CaseIterable {
    case tiny = "tiny"
    case base = "base"
    case small = "small"
    case medium = "medium"

    var displayName: String {
        switch self {
        case .tiny: return "Tiny (75MB, fastest)"
        case .base: return "Base (150MB, fast)"
        case .small: return "Small (500MB, recommended)"
        case .medium: return "Medium (1.5GB, highest accuracy)"
        }
    }

    var modelFilename: String {
        "ggml-\(rawValue).en.bin"
    }
}

// MARK: - Transcription Status

enum TranscriptionStatus {
    case idle
    case transcribing(file: String, progress: Int, total: Int)
    case completed(count: Int)
    case error(String)

    var isTranscribing: Bool {
        if case .transcribing = self { return true }
        return false
    }

    var displayText: String {
        switch self {
        case .idle:
            return "Ready"
        case .transcribing(let file, let progress, let total):
            return "Transcribing \(progress)/\(total): \(file)"
        case .completed(let count):
            return "Completed \(count) transcriptions"
        case .error(let msg):
            return "Error: \(msg)"
        }
    }
}

// MARK: - Whisper Status

enum WhisperStatus {
    case notInstalled
    case noModel
    case ready

    var displayText: String {
        switch self {
        case .notInstalled: return "Not installed"
        case .noModel: return "Model not downloaded"
        case .ready: return "Ready"
        }
    }
}

// MARK: - Transcription Manager

class TranscriptionManager {
    static let shared = TranscriptionManager()

    private(set) var status: TranscriptionStatus = .idle
    private(set) var lastTranscription: String?

    var onStatusChanged: ((TranscriptionStatus) -> Void)?
    var onProgress: ((String) -> Void)?

    private let configPath = Paths.configDir + "/transcription-config.json"

    private var shouldStop = false

    private init() {
        try? FileManager.default.createDirectory(atPath: Paths.whisperModelsDir, withIntermediateDirectories: true)
    }

    // MARK: - Configuration

    func loadConfig() -> TranscriptionConfig {
        guard FileManager.default.fileExists(atPath: configPath) else {
            return .default
        }

        do {
            let data = try Data(contentsOf: URL(fileURLWithPath: configPath))
            return try JSONDecoder().decode(TranscriptionConfig.self, from: data)
        } catch {
            logError("Failed to load transcription config: \(error.localizedDescription)")
            return .default
        }
    }

    func saveConfig(_ config: TranscriptionConfig) -> Bool {
        do {
            let configDir = (configPath as NSString).deletingLastPathComponent
            try FileManager.default.createDirectory(atPath: configDir, withIntermediateDirectories: true)

            let encoder = JSONEncoder()
            encoder.outputFormatting = .prettyPrinted
            let data = try encoder.encode(config)
            try data.write(to: URL(fileURLWithPath: configPath))
            logInfo("Transcription configuration saved")
            return true
        } catch {
            logError("Failed to save transcription config: \(error.localizedDescription)")
            return false
        }
    }

    // MARK: - Whisper Status

    func checkWhisperStatus() -> WhisperStatus {
        let whisperCheck = runShellCommand("which whisper-cli 2>/dev/null || which /opt/homebrew/bin/whisper-cli 2>/dev/null", timeout: 5)
        guard whisperCheck.success && !whisperCheck.output.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty else {
            return .notInstalled
        }

        let config = loadConfig()
        let modelPath = getModelPath(for: config.model)
        guard FileManager.default.fileExists(atPath: modelPath) else {
            return .noModel
        }

        return .ready
    }

    func getWhisperPath() -> String? {
        let paths = [
            "/opt/homebrew/bin/whisper-cli",
            "/usr/local/bin/whisper-cli"
        ]

        for path in paths {
            if FileManager.default.fileExists(atPath: path) {
                return path
            }
        }

        let result = runShellCommand("which whisper-cli 2>/dev/null", timeout: 5)
        if result.success && !result.output.isEmpty {
            return result.output.trimmingCharacters(in: .whitespacesAndNewlines)
        }

        return nil
    }

    func getModelPath(for model: String) -> String {
        return Paths.whisperModelsDir + "/ggml-\(model).en.bin"
    }

    func getAvailableModels() -> [String] {
        guard let contents = try? FileManager.default.contentsOfDirectory(atPath: Paths.whisperModelsDir) else {
            return []
        }

        return contents
            .filter { $0.hasPrefix("ggml-") && $0.hasSuffix(".bin") }
            .map { filename in
                filename
                    .replacingOccurrences(of: "ggml-", with: "")
                    .replacingOccurrences(of: ".en.bin", with: "")
                    .replacingOccurrences(of: ".bin", with: "")
            }
    }

    // MARK: - Transcription

    func transcribeVideo(at videoPath: String, completion: ((Bool, String?) -> Void)? = nil) {
        let config = loadConfig()

        guard config.enabled else {
            logInfo("Transcription disabled")
            completion?(false, nil)
            return
        }

        guard let whisperPath = getWhisperPath() else {
            logError("whisper-cli not found")
            status = .error("whisper-cli not installed")
            onStatusChanged?(status)
            completion?(false, nil)
            return
        }

        let modelPath = getModelPath(for: config.model)
        guard FileManager.default.fileExists(atPath: modelPath) else {
            logError("Whisper model not found: \(modelPath)")
            status = .error("Model not downloaded")
            onStatusChanged?(status)
            completion?(false, nil)
            return
        }

        guard FileManager.default.fileExists(atPath: videoPath) else {
            logError("Video file not found: \(videoPath)")
            completion?(false, nil)
            return
        }

        let videoDir = (videoPath as NSString).deletingLastPathComponent
        let videoName = ((videoPath as NSString).lastPathComponent as NSString).deletingPathExtension
        let outputBasePath = videoDir + "/" + videoName

        // Check if transcript already exists
        let txtPath = outputBasePath + ".txt"
        if FileManager.default.fileExists(atPath: txtPath) {
            logInfo("Transcript already exists: \(txtPath)")
            completion?(true, txtPath)
            return
        }

        let videoFilename = (videoPath as NSString).lastPathComponent
        logInfo("Starting transcription of: \(videoFilename)")

        onProgress?("Transcribing: \(videoFilename)")

        DispatchQueue.global(qos: .userInitiated).async { [weak self] in
            guard let self = self else { return }

            // Convert video to WAV for Whisper
            let wavPath = videoDir + "/\(videoName)_temp.wav"
            let ffmpegPath = "/opt/homebrew/bin/ffmpeg"

            let convertCommand = "\"\(ffmpegPath)\" -i \"\(videoPath)\" -ar 16000 -ac 1 -c:a pcm_s16le \"\(wavPath)\" -y 2>&1"
            logInfo("Converting to WAV: \(videoFilename)")
            let convertResult = runShellCommand(convertCommand, timeout: 300)

            guard FileManager.default.fileExists(atPath: wavPath) else {
                logError("Failed to convert to WAV: \(convertResult.output)")
                DispatchQueue.main.async {
                    self.status = .error("Audio conversion failed")
                    self.onStatusChanged?(self.status)
                    completion?(false, nil)
                }
                return
            }

            // Run Whisper
            var command = "\"\(whisperPath)\" -m \"\(modelPath)\" -f \"\(wavPath)\""

            switch config.outputFormat {
            case "txt":
                command += " -otxt"
            case "srt":
                command += " -osrt"
            case "vtt":
                command += " -ovtt"
            case "both":
                command += " -otxt -osrt"
            default:
                command += " -otxt"
            }

            command += " -of \"\(outputBasePath)\""

            if config.language != "auto" {
                command += " -l \(config.language)"
            }

            logInfo("Running Whisper: \(command)")
            let result = runShellCommand(command, timeout: 1800) // 30 min timeout for long videos

            // Cleanup temp WAV
            try? FileManager.default.removeItem(atPath: wavPath)

            DispatchQueue.main.async {
                let resultTxtPath = outputBasePath + ".txt"
                let resultSrtPath = outputBasePath + ".srt"

                var transcriptPath: String?
                if FileManager.default.fileExists(atPath: resultTxtPath) {
                    transcriptPath = resultTxtPath
                } else if FileManager.default.fileExists(atPath: resultSrtPath) {
                    transcriptPath = resultSrtPath
                }

                if let path = transcriptPath {
                    let transcript = (try? String(contentsOfFile: path, encoding: .utf8)) ?? ""
                    self.lastTranscription = transcript
                    logSuccess("Transcription completed: \((path as NSString).lastPathComponent)")
                    completion?(true, path)
                } else {
                    logError("Transcription failed: \(result.output)")
                    completion?(false, nil)
                }
            }
        }
    }

    func transcribeAllPending(completion: @escaping (Int, Int) -> Void) {
        let videos = StateManager.shared.getVideosForTranscription()

        guard !videos.isEmpty else {
            logInfo("No videos to transcribe")
            status = .completed(count: 0)
            onStatusChanged?(status)
            completion(0, 0)
            return
        }

        shouldStop = false
        var completed = 0
        var failed = 0
        let total = videos.count

        func transcribeNext(index: Int) {
            guard !shouldStop, index < videos.count else {
                status = .completed(count: completed)
                onStatusChanged?(status)
                completion(completed, failed)
                return
            }

            let video = videos[index]
            status = .transcribing(file: video.name, progress: index + 1, total: total)
            onStatusChanged?(status)

            transcribeVideo(at: video.localPath) { success, _ in
                if success {
                    completed += 1
                    var updatedFile = video
                    updatedFile.transcriptionStatus = .complete
                    updatedFile.transcribedAt = ISO8601DateFormatter().string(from: Date())
                    StateManager.shared.updateDriveFile(updatedFile)
                } else {
                    failed += 1
                    var updatedFile = video
                    updatedFile.transcriptionStatus = .error
                    StateManager.shared.updateDriveFile(updatedFile)
                }

                transcribeNext(index: index + 1)
            }
        }

        transcribeNext(index: 0)
    }

    // MARK: - Model Download

    func downloadModel(_ model: TranscriptionModel, progress: ((String) -> Void)? = nil, completion: @escaping (Bool) -> Void) {
        let modelPath = getModelPath(for: model.rawValue)

        if FileManager.default.fileExists(atPath: modelPath) {
            logInfo("Model already exists: \(model.rawValue)")
            completion(true)
            return
        }

        let url = "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/\(model.modelFilename)"

        logInfo("Downloading model: \(model.rawValue)")
        progress?("Downloading \(model.displayName)...")

        DispatchQueue.global(qos: .userInitiated).async {
            try? FileManager.default.createDirectory(atPath: Paths.whisperModelsDir, withIntermediateDirectories: true)

            let command = "curl -L \"\(url)\" -o \"\(modelPath)\" --progress-bar 2>&1"
            let result = runShellCommand(command, timeout: 600)

            DispatchQueue.main.async {
                if FileManager.default.fileExists(atPath: modelPath) {
                    logSuccess("Model downloaded: \(model.rawValue)")
                    progress?("Model downloaded successfully")
                    completion(true)
                } else {
                    logError("Failed to download model: \(result.output)")
                    progress?("Download failed")
                    completion(false)
                }
            }
        }
    }

    // MARK: - Control

    func stop() {
        shouldStop = true
    }

    func reset() {
        status = .idle
        lastTranscription = nil
        shouldStop = false
        onStatusChanged?(status)
    }
}
