import Foundation

// MARK: - Drive File Info

struct DriveFile: Codable {
    let id: String
    let name: String
    let mimeType: String
    let size: String?
    let modifiedTime: String?
    let parents: [String]?

    var sizeInt64: Int64 {
        return Int64(size ?? "0") ?? 0
    }

    var isFolder: Bool {
        return mimeType == "application/vnd.google-apps.folder"
    }

    var isVideo: Bool {
        let videoTypes = ["video/mp4", "video/quicktime", "video/x-msvideo", "video/webm", "video/3gpp", "video/mpeg", "video/x-matroska"]
        return videoTypes.contains(mimeType)
    }

    var isDocument: Bool {
        let docTypes = [
            "application/pdf",
            "application/vnd.google-apps.document",
            "application/vnd.google-apps.spreadsheet",
            "application/vnd.google-apps.presentation",
            "application/msword",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "application/vnd.ms-excel",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "application/vnd.ms-powerpoint",
            "application/vnd.openxmlformats-officedocument.presentationml.presentation"
        ]
        return docTypes.contains(mimeType)
    }

    var isGoogleDoc: Bool {
        return mimeType.contains("vnd.google-apps")
    }

    var exportMimeType: String? {
        switch mimeType {
        case "application/vnd.google-apps.document":
            return "application/pdf"
        case "application/vnd.google-apps.spreadsheet":
            return "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        case "application/vnd.google-apps.presentation":
            return "application/vnd.openxmlformats-officedocument.presentationml.presentation"
        default:
            return nil
        }
    }

    var exportExtension: String? {
        switch mimeType {
        case "application/vnd.google-apps.document":
            return ".pdf"
        case "application/vnd.google-apps.spreadsheet":
            return ".xlsx"
        case "application/vnd.google-apps.presentation":
            return ".pptx"
        default:
            return nil
        }
    }
}

// MARK: - Drive Files List Response

struct DriveFilesListResponse: Codable {
    let files: [DriveFile]?
    let nextPageToken: String?
}

// MARK: - Drive Client

class DriveClient {
    static let shared = DriveClient()

    private let baseUrl = "https://www.googleapis.com/drive/v3"

    var onProgress: ((String) -> Void)?
    var onFileFound: ((DriveFile) -> Void)?

    private var isRunning = false
    private var shouldStop = false

    private init() {}

    // MARK: - File Listing

    func listFiles(query: String? = nil, pageToken: String? = nil, completion: @escaping (Result<DriveFilesListResponse, Error>) -> Void) {
        GoogleAuthManager.shared.getAccessToken { [weak self] accessToken in
            guard let self = self, let token = accessToken else {
                completion(.failure(NSError(domain: "DriveClient", code: 401, userInfo: [NSLocalizedDescriptionKey: "No access token"])))
                return
            }

            var urlString = "\(self.baseUrl)/files?fields=files(id,name,mimeType,size,modifiedTime,parents),nextPageToken&pageSize=100"

            if let query = query {
                let encodedQuery = query.addingPercentEncoding(withAllowedCharacters: .urlQueryAllowed) ?? query
                urlString += "&q=\(encodedQuery)"
            }

            if let pageToken = pageToken {
                urlString += "&pageToken=\(pageToken)"
            }

            let curlCommand = "curl -s '\(urlString)' -H 'Authorization: Bearer \(token)'"

            DispatchQueue.global(qos: .userInitiated).async {
                let result = runShellCommand(curlCommand, timeout: 60)

                DispatchQueue.main.async {
                    guard result.success, let data = result.output.data(using: .utf8) else {
                        completion(.failure(NSError(domain: "DriveClient", code: -1, userInfo: [NSLocalizedDescriptionKey: result.output])))
                        return
                    }

                    do {
                        let response = try JSONDecoder().decode(DriveFilesListResponse.self, from: data)
                        completion(.success(response))
                    } catch {
                        completion(.failure(error))
                    }
                }
            }
        }
    }

    func listAllVideosAndDocuments(completion: @escaping ([DriveFile]) -> Void) {
        var allFiles: [DriveFile] = []
        let config = ConfigManager.shared.loadConfig()

        // Build query for videos and documents
        var queryParts: [String] = ["trashed = false"]

        var mimeTypes: [String] = []
        if config.downloadVideos {
            mimeTypes += [
                "video/mp4",
                "video/quicktime",
                "video/x-msvideo",
                "video/webm",
                "video/3gpp",
                "video/mpeg",
                "video/x-matroska"
            ]
        }
        if config.downloadDocuments {
            mimeTypes += [
                "application/pdf",
                "application/vnd.google-apps.document",
                "application/vnd.google-apps.spreadsheet",
                "application/vnd.google-apps.presentation"
            ]
        }

        if !mimeTypes.isEmpty {
            let mimeQuery = mimeTypes.map { "mimeType = '\($0)'" }.joined(separator: " or ")
            queryParts.append("(\(mimeQuery))")
        }

        let query = queryParts.joined(separator: " and ")

        func fetchPage(pageToken: String?) {
            guard !shouldStop else {
                completion(allFiles)
                return
            }

            listFiles(query: query, pageToken: pageToken) { [weak self] result in
                switch result {
                case .success(let response):
                    if let files = response.files {
                        allFiles.append(contentsOf: files)
                        files.forEach { self?.onFileFound?($0) }
                        self?.onProgress?("Found \(allFiles.count) files...")
                    }

                    if let nextToken = response.nextPageToken {
                        fetchPage(pageToken: nextToken)
                    } else {
                        completion(allFiles)
                    }

                case .failure(let error):
                    logError("Failed to list files: \(error.localizedDescription)")
                    completion(allFiles)
                }
            }
        }

        onProgress?("Scanning Google Drive...")
        fetchPage(pageToken: nil)
    }

    // MARK: - File Download

    func downloadFile(_ file: DriveFile, to destinationDir: String, completion: @escaping (Bool, String?) -> Void) {
        GoogleAuthManager.shared.getAccessToken { [weak self] accessToken in
            guard let self = self, let token = accessToken else {
                completion(false, "No access token")
                return
            }

            let fileManager = FileManager.default
            try? fileManager.createDirectory(atPath: destinationDir, withIntermediateDirectories: true)

            var filename = file.name
            var downloadUrl: String

            if file.isGoogleDoc, let exportMime = file.exportMimeType, let ext = file.exportExtension {
                // Export Google Docs format
                let encodedMime = exportMime.addingPercentEncoding(withAllowedCharacters: .urlQueryAllowed) ?? exportMime
                downloadUrl = "\(self.baseUrl)/files/\(file.id)/export?mimeType=\(encodedMime)"
                if !filename.hasSuffix(ext) {
                    filename += ext
                }
            } else {
                // Direct download
                downloadUrl = "\(self.baseUrl)/files/\(file.id)?alt=media"
            }

            let destinationPath = destinationDir + "/" + filename

            // Check if file already exists
            if fileManager.fileExists(atPath: destinationPath) {
                logInfo("File already exists: \(filename)")
                completion(true, destinationPath)
                return
            }

            self.onProgress?("Downloading: \(filename)")

            let curlCommand = "curl -L -s '\(downloadUrl)' -H 'Authorization: Bearer \(token)' -o '\(destinationPath)'"

            DispatchQueue.global(qos: .userInitiated).async {
                let result = runShellCommand(curlCommand, timeout: 600)

                DispatchQueue.main.async {
                    if fileManager.fileExists(atPath: destinationPath) {
                        // Verify file isn't empty or an error response
                        if let attrs = try? fileManager.attributesOfItem(atPath: destinationPath),
                           let size = attrs[.size] as? Int64,
                           size > 0 {
                            logSuccess("Downloaded: \(filename)")
                            completion(true, destinationPath)
                        } else {
                            try? fileManager.removeItem(atPath: destinationPath)
                            completion(false, "Downloaded file is empty or invalid")
                        }
                    } else {
                        completion(false, result.output)
                    }
                }
            }
        }
    }

    // MARK: - Control

    func stop() {
        shouldStop = true
    }

    func reset() {
        shouldStop = false
        isRunning = false
    }
}
