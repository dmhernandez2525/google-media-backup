import Foundation

// MARK: - Photos Media Item

struct PhotosMediaItem: Codable {
    let id: String
    let filename: String
    let mimeType: String
    let baseUrl: String
    let mediaMetadata: MediaMetadata?

    struct MediaMetadata: Codable {
        let width: String?
        let height: String?
        let video: VideoMetadata?

        struct VideoMetadata: Codable {
            let fps: Double?
            let status: String?
        }
    }

    var isVideo: Bool {
        return mimeType.hasPrefix("video/") || mediaMetadata?.video != nil
    }

    var downloadUrl: String {
        if isVideo {
            return baseUrl + "=dv" // dv = download video
        } else {
            return baseUrl + "=d" // d = download
        }
    }
}

// MARK: - Photos List Response

struct PhotosListResponse: Codable {
    let mediaItems: [PhotosMediaItem]?
    let nextPageToken: String?
}

// MARK: - Photos Client

class PhotosClient {
    static let shared = PhotosClient()

    private let baseUrl = "https://photoslibrary.googleapis.com/v1"

    var onProgress: ((String) -> Void)?
    var onMediaFound: ((PhotosMediaItem) -> Void)?

    private var shouldStop = false

    private init() {}

    // MARK: - Media Listing

    func listMediaItems(pageToken: String? = nil, completion: @escaping (Result<PhotosListResponse, Error>) -> Void) {
        GoogleAuthManager.shared.getAccessToken { [weak self] accessToken in
            guard let self = self, let token = accessToken else {
                completion(.failure(NSError(domain: "PhotosClient", code: 401, userInfo: [NSLocalizedDescriptionKey: "No access token"])))
                return
            }

            var body: [String: Any] = ["pageSize": 100]
            if let pageToken = pageToken {
                body["pageToken"] = pageToken
            }

            guard let bodyData = try? JSONSerialization.data(withJSONObject: body) else {
                completion(.failure(NSError(domain: "PhotosClient", code: -1, userInfo: [NSLocalizedDescriptionKey: "Failed to encode request"])))
                return
            }

            let bodyString = String(data: bodyData, encoding: .utf8) ?? "{}"

            let curlCommand = """
            curl -s '\(self.baseUrl)/mediaItems:search' \
                -H 'Authorization: Bearer \(token)' \
                -H 'Content-Type: application/json' \
                -d '\(bodyString)'
            """

            DispatchQueue.global(qos: .userInitiated).async {
                let result = runShellCommand(curlCommand, timeout: 60)

                DispatchQueue.main.async {
                    guard result.success, let data = result.output.data(using: .utf8) else {
                        completion(.failure(NSError(domain: "PhotosClient", code: -1, userInfo: [NSLocalizedDescriptionKey: result.output])))
                        return
                    }

                    do {
                        let response = try JSONDecoder().decode(PhotosListResponse.self, from: data)
                        completion(.success(response))
                    } catch {
                        completion(.failure(error))
                    }
                }
            }
        }
    }

    func listAllVideos(completion: @escaping ([PhotosMediaItem]) -> Void) {
        var allVideos: [PhotosMediaItem] = []
        let config = ConfigManager.shared.loadConfig()

        guard config.downloadPhotos else {
            completion([])
            return
        }

        func fetchPage(pageToken: String?) {
            guard !shouldStop else {
                completion(allVideos)
                return
            }

            listMediaItems(pageToken: pageToken) { [weak self] result in
                switch result {
                case .success(let response):
                    if let items = response.mediaItems {
                        let videos = items.filter { $0.isVideo }
                        allVideos.append(contentsOf: videos)
                        videos.forEach { self?.onMediaFound?($0) }
                        self?.onProgress?("Found \(allVideos.count) videos in Photos...")
                    }

                    if let nextToken = response.nextPageToken {
                        fetchPage(pageToken: nextToken)
                    } else {
                        completion(allVideos)
                    }

                case .failure(let error):
                    logError("Failed to list photos: \(error.localizedDescription)")
                    completion(allVideos)
                }
            }
        }

        onProgress?("Scanning Google Photos...")
        fetchPage(pageToken: nil)
    }

    // MARK: - Media Download

    func downloadMedia(_ item: PhotosMediaItem, to destinationDir: String, completion: @escaping (Bool, String?) -> Void) {
        let fileManager = FileManager.default
        try? fileManager.createDirectory(atPath: destinationDir, withIntermediateDirectories: true)

        let destinationPath = destinationDir + "/" + item.filename

        // Check if file already exists
        if fileManager.fileExists(atPath: destinationPath) {
            logInfo("File already exists: \(item.filename)")
            completion(true, destinationPath)
            return
        }

        onProgress?("Downloading: \(item.filename)")

        let curlCommand = "curl -L -s '\(item.downloadUrl)' -o '\(destinationPath)'"

        DispatchQueue.global(qos: .userInitiated).async {
            let result = runShellCommand(curlCommand, timeout: 600)

            DispatchQueue.main.async {
                if fileManager.fileExists(atPath: destinationPath) {
                    if let attrs = try? fileManager.attributesOfItem(atPath: destinationPath),
                       let size = attrs[.size] as? Int64,
                       size > 0 {
                        logSuccess("Downloaded: \(item.filename)")
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

    // MARK: - Control

    func stop() {
        shouldStop = true
    }

    func reset() {
        shouldStop = false
    }
}
