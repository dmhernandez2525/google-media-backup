import Foundation

// MARK: - App Configuration

struct AppConfig: Codable {
    var downloadPath: String
    var autoDownload: Bool
    var autoTranscribe: Bool
    var transcriptionModel: String
    var downloadVideos: Bool
    var downloadDocuments: Bool
    var downloadPhotos: Bool
    var maxConcurrentDownloads: Int
    var excludePatterns: [String]

    enum CodingKeys: String, CodingKey {
        case downloadPath = "download_path"
        case autoDownload = "auto_download"
        case autoTranscribe = "auto_transcribe"
        case transcriptionModel = "transcription_model"
        case downloadVideos = "download_videos"
        case downloadDocuments = "download_documents"
        case downloadPhotos = "download_photos"
        case maxConcurrentDownloads = "max_concurrent_downloads"
        case excludePatterns = "exclude_patterns"
    }

    static var `default`: AppConfig {
        AppConfig(
            downloadPath: Paths.downloadBase,
            autoDownload: false,
            autoTranscribe: true,
            transcriptionModel: "small",
            downloadVideos: true,
            downloadDocuments: true,
            downloadPhotos: true,
            maxConcurrentDownloads: 3,
            excludePatterns: [".DS_Store", "*.tmp", "*.part"]
        )
    }
}

// MARK: - Config Manager

class ConfigManager {
    static let shared = ConfigManager()

    private init() {
        try? FileManager.default.createDirectory(atPath: Paths.configDir, withIntermediateDirectories: true)
        try? FileManager.default.createDirectory(atPath: Paths.stateDir, withIntermediateDirectories: true)
        try? FileManager.default.createDirectory(atPath: Paths.downloadBase, withIntermediateDirectories: true)
    }

    func loadConfig() -> AppConfig {
        guard FileManager.default.fileExists(atPath: Paths.configPath) else {
            logInfo("No config file found, using defaults")
            return .default
        }

        do {
            let data = try Data(contentsOf: URL(fileURLWithPath: Paths.configPath))
            let config = try JSONDecoder().decode(AppConfig.self, from: data)
            logInfo("Loaded config: downloadPath=\(config.downloadPath)")
            return config
        } catch {
            logError("Failed to load config: \(error.localizedDescription)")
            return .default
        }
    }

    func saveConfig(_ config: AppConfig) -> Bool {
        do {
            let encoder = JSONEncoder()
            encoder.outputFormatting = .prettyPrinted
            let data = try encoder.encode(config)
            try data.write(to: URL(fileURLWithPath: Paths.configPath))
            logInfo("Config saved")
            return true
        } catch {
            logError("Failed to save config: \(error.localizedDescription)")
            return false
        }
    }
}

// MARK: - File State

struct FileState: Codable, Identifiable {
    let id: String
    var name: String
    var mimeType: String
    var size: Int64
    var localPath: String
    var downloadStatus: DownloadStatus
    var transcriptionStatus: TranscriptionFileStatus
    var error: String?
    var downloadedAt: String?
    var transcribedAt: String?
    var modifiedTime: String?

    enum CodingKeys: String, CodingKey {
        case id
        case name
        case mimeType = "mime_type"
        case size
        case localPath = "local_path"
        case downloadStatus = "download_status"
        case transcriptionStatus = "transcription_status"
        case error
        case downloadedAt = "downloaded_at"
        case transcribedAt = "transcribed_at"
        case modifiedTime = "modified_time"
    }

    enum DownloadStatus: String, Codable {
        case pending
        case downloading
        case complete
        case error
    }

    enum TranscriptionFileStatus: String, Codable {
        case pending
        case processing
        case complete
        case error
        case notApplicable = "n/a"
    }

    var isVideo: Bool {
        let videoTypes = ["video/mp4", "video/quicktime", "video/x-msvideo", "video/webm", "video/3gpp", "video/mpeg"]
        return videoTypes.contains(mimeType)
    }
}

// MARK: - Sync State

struct SyncState: Codable {
    var lastSyncTime: String?
    var files: [String: FileState]
    var totalFiles: Int
    var completedFiles: Int
    var errorFiles: Int

    enum CodingKeys: String, CodingKey {
        case lastSyncTime = "last_sync_time"
        case files
        case totalFiles = "total_files"
        case completedFiles = "completed_files"
        case errorFiles = "error_files"
    }

    static var empty: SyncState {
        SyncState(lastSyncTime: nil, files: [:], totalFiles: 0, completedFiles: 0, errorFiles: 0)
    }
}

// MARK: - State Manager

class StateManager {
    static let shared = StateManager()

    private(set) var driveState: SyncState = .empty
    private(set) var photosState: SyncState = .empty

    private init() {
        loadStates()
    }

    func loadStates() {
        driveState = loadState(from: Paths.driveStatePath) ?? .empty
        photosState = loadState(from: Paths.photosStatePath) ?? .empty
    }

    private func loadState(from path: String) -> SyncState? {
        guard FileManager.default.fileExists(atPath: path) else { return nil }

        do {
            let data = try Data(contentsOf: URL(fileURLWithPath: path))
            return try JSONDecoder().decode(SyncState.self, from: data)
        } catch {
            logError("Failed to load state from \(path): \(error.localizedDescription)")
            return nil
        }
    }

    func saveDriveState() {
        saveState(driveState, to: Paths.driveStatePath)
    }

    func savePhotosState() {
        saveState(photosState, to: Paths.photosStatePath)
    }

    private func saveState(_ state: SyncState, to path: String) {
        do {
            let encoder = JSONEncoder()
            encoder.outputFormatting = .prettyPrinted
            let data = try encoder.encode(state)
            try data.write(to: URL(fileURLWithPath: path))
        } catch {
            logError("Failed to save state to \(path): \(error.localizedDescription)")
        }
    }

    func updateDriveFile(_ file: FileState) {
        driveState.files[file.id] = file
        updateCounts(&driveState)
        saveDriveState()
    }

    func updatePhotosFile(_ file: FileState) {
        photosState.files[file.id] = file
        updateCounts(&photosState)
        savePhotosState()
    }

    private func updateCounts(_ state: inout SyncState) {
        state.totalFiles = state.files.count
        state.completedFiles = state.files.values.filter { $0.downloadStatus == .complete }.count
        state.errorFiles = state.files.values.filter { $0.downloadStatus == .error }.count
    }

    func getAllFiles() -> [FileState] {
        let driveFiles = Array(driveState.files.values)
        let photosFiles = Array(photosState.files.values)
        return (driveFiles + photosFiles).sorted { ($0.downloadedAt ?? "") > ($1.downloadedAt ?? "") }
    }

    func getVideosForTranscription() -> [FileState] {
        return getAllFiles().filter {
            $0.isVideo &&
            $0.downloadStatus == .complete &&
            $0.transcriptionStatus == .pending
        }
    }

    func resetState() {
        driveState = .empty
        photosState = .empty
        saveDriveState()
        savePhotosState()
    }
}
