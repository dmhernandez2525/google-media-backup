import Foundation

// MARK: - Download Status

enum OverallDownloadStatus {
    case idle
    case scanning
    case downloading(current: Int, total: Int, filename: String)
    case paused
    case completed(downloaded: Int, skipped: Int, errors: Int)
    case error(String)

    var isActive: Bool {
        switch self {
        case .scanning, .downloading: return true
        default: return false
        }
    }

    var displayText: String {
        switch self {
        case .idle:
            return "Ready"
        case .scanning:
            return "Scanning..."
        case .downloading(let current, let total, let filename):
            return "Downloading \(current)/\(total): \(filename)"
        case .paused:
            return "Paused"
        case .completed(let downloaded, let skipped, let errors):
            var parts = ["\(downloaded) downloaded"]
            if skipped > 0 { parts.append("\(skipped) skipped") }
            if errors > 0 { parts.append("\(errors) errors") }
            return parts.joined(separator: ", ")
        case .error(let msg):
            return "Error: \(msg)"
        }
    }
}

// MARK: - Download Manager

class DownloadManager {
    static let shared = DownloadManager()

    private(set) var status: OverallDownloadStatus = .idle
    private(set) var driveFiles: [DriveFile] = []
    private(set) var photosFiles: [PhotosMediaItem] = []

    var onStatusChanged: ((OverallDownloadStatus) -> Void)?
    var onProgress: ((String) -> Void)?
    var onFileDownloaded: ((FileState) -> Void)?

    private var shouldStop = false
    private var isPaused = false

    private init() {}

    // MARK: - Start Download

    func startDownload(completion: @escaping (Int, Int, Int) -> Void) {
        guard !GoogleAuthManager.shared.status.isReady else {
            // Auth is ready, proceed
            performDownload(completion: completion)
            return
        }

        status = .error("Not authenticated")
        onStatusChanged?(status)
        completion(0, 0, 1)
    }

    private func performDownload(completion: @escaping (Int, Int, Int) -> Void) {
        shouldStop = false
        isPaused = false

        status = .scanning
        onStatusChanged?(status)
        onProgress?("Scanning Google Drive and Photos...")

        // Scan Drive and Photos in parallel
        let group = DispatchGroup()

        group.enter()
        DriveClient.shared.onProgress = { [weak self] msg in
            self?.onProgress?(msg)
        }
        DriveClient.shared.listAllVideosAndDocuments { [weak self] files in
            self?.driveFiles = files
            group.leave()
        }

        group.enter()
        PhotosClient.shared.onProgress = { [weak self] msg in
            self?.onProgress?(msg)
        }
        PhotosClient.shared.listAllVideos { [weak self] items in
            self?.photosFiles = items
            group.leave()
        }

        group.notify(queue: .main) { [weak self] in
            guard let self = self else { return }

            let totalDrive = self.driveFiles.count
            let totalPhotos = self.photosFiles.count
            let totalFiles = totalDrive + totalPhotos

            logInfo("Found \(totalDrive) Drive files, \(totalPhotos) Photos videos")
            self.onProgress?("Found \(totalFiles) files to process")

            if totalFiles == 0 {
                self.status = .completed(downloaded: 0, skipped: 0, errors: 0)
                self.onStatusChanged?(self.status)
                completion(0, 0, 0)
                return
            }

            self.downloadAllFiles(completion: completion)
        }
    }

    private func downloadAllFiles(completion: @escaping (Int, Int, Int) -> Void) {
        let config = ConfigManager.shared.loadConfig()
        let downloadDir = config.downloadPath

        var downloaded = 0
        var skipped = 0
        var errors = 0
        var currentIndex = 0

        let totalFiles = driveFiles.count + photosFiles.count

        func downloadNext() {
            guard !shouldStop else {
                status = .completed(downloaded: downloaded, skipped: skipped, errors: errors)
                onStatusChanged?(status)
                completion(downloaded, skipped, errors)
                return
            }

            while isPaused {
                Thread.sleep(forTimeInterval: 0.5)
                if shouldStop {
                    status = .completed(downloaded: downloaded, skipped: skipped, errors: errors)
                    onStatusChanged?(status)
                    completion(downloaded, skipped, errors)
                    return
                }
            }

            if currentIndex < driveFiles.count {
                // Download Drive file
                let file = driveFiles[currentIndex]
                currentIndex += 1

                // Check if already downloaded
                let existingState = StateManager.shared.driveState.files[file.id]
                if existingState?.downloadStatus == .complete {
                    skipped += 1
                    downloadNext()
                    return
                }

                status = .downloading(current: currentIndex, total: totalFiles, filename: file.name)
                onStatusChanged?(status)

                // Determine subdirectory based on file type
                let subDir: String
                if file.isVideo {
                    subDir = "Videos/Drive"
                } else if file.isDocument {
                    subDir = "Documents"
                } else {
                    subDir = "Other"
                }

                let destDir = downloadDir + "/" + subDir

                DriveClient.shared.downloadFile(file, to: destDir) { [weak self] success, localPath in
                    let fileState = FileState(
                        id: file.id,
                        name: file.name,
                        mimeType: file.mimeType,
                        size: file.sizeInt64,
                        localPath: localPath ?? "",
                        downloadStatus: success ? .complete : .error,
                        transcriptionStatus: file.isVideo ? .pending : .notApplicable,
                        error: success ? nil : "Download failed",
                        downloadedAt: success ? ISO8601DateFormatter().string(from: Date()) : nil,
                        transcribedAt: nil,
                        modifiedTime: file.modifiedTime
                    )

                    StateManager.shared.updateDriveFile(fileState)
                    self?.onFileDownloaded?(fileState)

                    if success {
                        downloaded += 1
                    } else {
                        errors += 1
                    }

                    downloadNext()
                }

            } else if currentIndex < driveFiles.count + photosFiles.count {
                // Download Photos file
                let photosIndex = currentIndex - driveFiles.count
                let item = photosFiles[photosIndex]
                currentIndex += 1

                // Check if already downloaded
                let existingState = StateManager.shared.photosState.files[item.id]
                if existingState?.downloadStatus == .complete {
                    skipped += 1
                    downloadNext()
                    return
                }

                status = .downloading(current: currentIndex, total: totalFiles, filename: item.filename)
                onStatusChanged?(status)

                let destDir = downloadDir + "/Videos/Photos"

                PhotosClient.shared.downloadMedia(item, to: destDir) { [weak self] success, localPath in
                    let fileState = FileState(
                        id: item.id,
                        name: item.filename,
                        mimeType: item.mimeType,
                        size: 0, // Size not available from Photos API
                        localPath: localPath ?? "",
                        downloadStatus: success ? .complete : .error,
                        transcriptionStatus: .pending,
                        error: success ? nil : "Download failed",
                        downloadedAt: success ? ISO8601DateFormatter().string(from: Date()) : nil,
                        transcribedAt: nil,
                        modifiedTime: nil
                    )

                    StateManager.shared.updatePhotosFile(fileState)
                    self?.onFileDownloaded?(fileState)

                    if success {
                        downloaded += 1
                    } else {
                        errors += 1
                    }

                    downloadNext()
                }

            } else {
                // All done
                status = .completed(downloaded: downloaded, skipped: skipped, errors: errors)
                onStatusChanged?(status)

                // Update state with last sync time
                var driveState = StateManager.shared.driveState
                driveState.lastSyncTime = ISO8601DateFormatter().string(from: Date())
                StateManager.shared.saveDriveState()

                var photosState = StateManager.shared.photosState
                photosState.lastSyncTime = ISO8601DateFormatter().string(from: Date())
                StateManager.shared.savePhotosState()

                logSuccess("Download complete: \(downloaded) downloaded, \(skipped) skipped, \(errors) errors")
                showSystemNotification(title: "Download Complete", body: "\(downloaded) files downloaded")

                completion(downloaded, skipped, errors)
            }
        }

        downloadNext()
    }

    // MARK: - Control

    func pause() {
        isPaused = true
        status = .paused
        onStatusChanged?(status)
    }

    func resume() {
        isPaused = false
    }

    func stop() {
        shouldStop = true
        DriveClient.shared.stop()
        PhotosClient.shared.stop()
    }

    func reset() {
        shouldStop = false
        isPaused = false
        status = .idle
        driveFiles = []
        photosFiles = []
        DriveClient.shared.reset()
        PhotosClient.shared.reset()
        onStatusChanged?(status)
    }

    // MARK: - Statistics

    func getStatistics() -> (total: Int, downloaded: Int, pending: Int, errors: Int, videosToTranscribe: Int) {
        let allFiles = StateManager.shared.getAllFiles()
        let total = allFiles.count
        let downloaded = allFiles.filter { $0.downloadStatus == .complete }.count
        let pending = allFiles.filter { $0.downloadStatus == .pending || $0.downloadStatus == .downloading }.count
        let errors = allFiles.filter { $0.downloadStatus == .error }.count
        let videosToTranscribe = StateManager.shared.getVideosForTranscription().count

        return (total, downloaded, pending, errors, videosToTranscribe)
    }
}
