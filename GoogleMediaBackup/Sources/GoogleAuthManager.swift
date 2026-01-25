import Cocoa

// MARK: - Google OAuth Configuration

struct GoogleOAuthConfig {
    static let clientId = "" // Will be loaded from credentials.json
    static let clientSecret = "" // Will be loaded from credentials.json
    static let redirectUri = "http://localhost:8080/callback"
    static let scopes = [
        "https://www.googleapis.com/auth/drive.readonly",
        "https://www.googleapis.com/auth/photoslibrary.readonly"
    ]
    static let authUrl = "https://accounts.google.com/o/oauth2/v2/auth"
    static let tokenUrl = "https://oauth2.googleapis.com/token"
}

// MARK: - OAuth Token

struct OAuthToken: Codable {
    var accessToken: String
    var refreshToken: String
    var expiresIn: Int
    var tokenType: String
    var scope: String
    var obtainedAt: Date

    enum CodingKeys: String, CodingKey {
        case accessToken = "access_token"
        case refreshToken = "refresh_token"
        case expiresIn = "expires_in"
        case tokenType = "token_type"
        case scope
        case obtainedAt = "obtained_at"
    }

    var isExpired: Bool {
        let expirationDate = obtainedAt.addingTimeInterval(TimeInterval(expiresIn - 60))
        return Date() >= expirationDate
    }
}

// MARK: - Credentials File

struct CredentialsFile: Codable {
    let installed: InstalledCredentials?
    let web: WebCredentials?

    struct InstalledCredentials: Codable {
        let clientId: String
        let clientSecret: String

        enum CodingKeys: String, CodingKey {
            case clientId = "client_id"
            case clientSecret = "client_secret"
        }
    }

    struct WebCredentials: Codable {
        let clientId: String
        let clientSecret: String

        enum CodingKeys: String, CodingKey {
            case clientId = "client_id"
            case clientSecret = "client_secret"
        }
    }
}

// MARK: - Auth Status

enum AuthStatus {
    case notConfigured
    case needsAuth
    case authenticated
    case error(String)

    var displayText: String {
        switch self {
        case .notConfigured: return "Not configured"
        case .needsAuth: return "Needs authorization"
        case .authenticated: return "Authenticated"
        case .error(let msg): return "Error: \(msg)"
        }
    }

    var isReady: Bool {
        if case .authenticated = self { return true }
        return false
    }
}

// MARK: - Google Auth Manager

class GoogleAuthManager {
    static let shared = GoogleAuthManager()

    private var clientId: String = ""
    private var clientSecret: String = ""
    private(set) var token: OAuthToken?
    private(set) var status: AuthStatus = .notConfigured

    var onAuthStatusChanged: ((AuthStatus) -> Void)?

    private init() {
        loadCredentials()
        loadToken()
        updateStatus()
    }

    // MARK: - Credentials Management

    private func loadCredentials() {
        guard FileManager.default.fileExists(atPath: Paths.credentialsPath) else {
            logInfo("No credentials.json found at \(Paths.credentialsPath)")
            return
        }

        do {
            let data = try Data(contentsOf: URL(fileURLWithPath: Paths.credentialsPath))
            let creds = try JSONDecoder().decode(CredentialsFile.self, from: data)

            if let installed = creds.installed {
                clientId = installed.clientId
                clientSecret = installed.clientSecret
                logInfo("Loaded installed credentials")
            } else if let web = creds.web {
                clientId = web.clientId
                clientSecret = web.clientSecret
                logInfo("Loaded web credentials")
            }
        } catch {
            logError("Failed to load credentials: \(error.localizedDescription)")
        }
    }

    func hasCredentials() -> Bool {
        return !clientId.isEmpty && !clientSecret.isEmpty
    }

    // MARK: - Token Management

    private func loadToken() {
        guard FileManager.default.fileExists(atPath: Paths.tokenPath) else {
            logInfo("No token.json found")
            return
        }

        do {
            let data = try Data(contentsOf: URL(fileURLWithPath: Paths.tokenPath))
            token = try JSONDecoder().decode(OAuthToken.self, from: data)
            logInfo("Loaded existing token")
        } catch {
            logError("Failed to load token: \(error.localizedDescription)")
        }
    }

    private func saveToken(_ token: OAuthToken) {
        do {
            let encoder = JSONEncoder()
            encoder.outputFormatting = .prettyPrinted
            encoder.dateEncodingStrategy = .iso8601
            let data = try encoder.encode(token)
            try data.write(to: URL(fileURLWithPath: Paths.tokenPath))
            self.token = token
            logInfo("Token saved")
        } catch {
            logError("Failed to save token: \(error.localizedDescription)")
        }
    }

    private func updateStatus() {
        if !hasCredentials() {
            status = .notConfigured
        } else if token == nil {
            status = .needsAuth
        } else if token?.isExpired == true {
            status = .needsAuth
        } else {
            status = .authenticated
        }
        onAuthStatusChanged?(status)
    }

    // MARK: - OAuth Flow

    func startAuthFlow(completion: @escaping (Bool, String?) -> Void) {
        guard hasCredentials() else {
            completion(false, "No credentials configured. Please add credentials.json")
            return
        }

        let scopeString = GoogleOAuthConfig.scopes.joined(separator: " ")
        let encodedScope = scopeString.addingPercentEncoding(withAllowedCharacters: .urlQueryAllowed) ?? ""
        let encodedRedirect = GoogleOAuthConfig.redirectUri.addingPercentEncoding(withAllowedCharacters: .urlQueryAllowed) ?? ""

        let authUrlString = "\(GoogleOAuthConfig.authUrl)?client_id=\(clientId)&redirect_uri=\(encodedRedirect)&response_type=code&scope=\(encodedScope)&access_type=offline&prompt=consent"

        guard let authUrl = URL(string: authUrlString) else {
            completion(false, "Invalid auth URL")
            return
        }

        logInfo("Opening browser for OAuth flow")

        // Start local server to receive callback
        startCallbackServer { [weak self] code in
            if let code = code {
                self?.exchangeCodeForToken(code: code, completion: completion)
            } else {
                completion(false, "Failed to receive authorization code")
            }
        }

        // Open browser
        NSWorkspace.shared.open(authUrl)
    }

    private func startCallbackServer(completion: @escaping (String?) -> Void) {
        DispatchQueue.global(qos: .userInitiated).async {
            // Simple HTTP server to catch OAuth callback
            let serverScript = """
            python3 -c '
import http.server
import socketserver
import urllib.parse
import sys

class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)
        code = params.get("code", [None])[0]

        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()

        if code:
            self.wfile.write(b"<html><body><h1>Authorization successful!</h1><p>You can close this window.</p></body></html>")
            print(code)
        else:
            self.wfile.write(b"<html><body><h1>Authorization failed</h1></body></html>")
            print("ERROR")

        # Signal shutdown
        def shutdown():
            httpd.shutdown()
        import threading
        threading.Thread(target=shutdown).start()

    def log_message(self, format, *args):
        pass

with socketserver.TCPServer(("", 8080), Handler) as httpd:
    httpd.handle_request()
' 2>&1
"""

            let result = runShellCommand(serverScript, timeout: 120)

            DispatchQueue.main.async {
                let code = result.output.trimmingCharacters(in: .whitespacesAndNewlines)
                if code.isEmpty || code == "ERROR" {
                    completion(nil)
                } else {
                    completion(code)
                }
            }
        }
    }

    private func exchangeCodeForToken(code: String, completion: @escaping (Bool, String?) -> Void) {
        let tokenParams = [
            "code": code,
            "client_id": clientId,
            "client_secret": clientSecret,
            "redirect_uri": GoogleOAuthConfig.redirectUri,
            "grant_type": "authorization_code"
        ]

        let bodyString = tokenParams.map { "\($0.key)=\($0.value)" }.joined(separator: "&")

        let curlCommand = """
        curl -s -X POST '\(GoogleOAuthConfig.tokenUrl)' \
            -H 'Content-Type: application/x-www-form-urlencoded' \
            -d '\(bodyString)'
        """

        DispatchQueue.global(qos: .userInitiated).async { [weak self] in
            let result = runShellCommand(curlCommand, timeout: 30)

            DispatchQueue.main.async {
                guard result.success else {
                    completion(false, "Token request failed: \(result.output)")
                    return
                }

                do {
                    guard let data = result.output.data(using: .utf8) else {
                        completion(false, "Invalid response data")
                        return
                    }

                    let json = try JSONSerialization.jsonObject(with: data) as? [String: Any]

                    guard let accessToken = json?["access_token"] as? String,
                          let refreshToken = json?["refresh_token"] as? String,
                          let expiresIn = json?["expires_in"] as? Int else {
                        let errorDesc = json?["error_description"] as? String ?? "Unknown error"
                        completion(false, errorDesc)
                        return
                    }

                    let token = OAuthToken(
                        accessToken: accessToken,
                        refreshToken: refreshToken,
                        expiresIn: expiresIn,
                        tokenType: json?["token_type"] as? String ?? "Bearer",
                        scope: json?["scope"] as? String ?? "",
                        obtainedAt: Date()
                    )

                    self?.saveToken(token)
                    self?.updateStatus()
                    logSuccess("OAuth flow completed successfully")
                    completion(true, nil)
                } catch {
                    completion(false, "Failed to parse token response: \(error.localizedDescription)")
                }
            }
        }
    }

    // MARK: - Token Refresh

    func refreshAccessToken(completion: @escaping (Bool) -> Void) {
        guard let currentToken = token else {
            completion(false)
            return
        }

        let refreshParams = [
            "refresh_token": currentToken.refreshToken,
            "client_id": clientId,
            "client_secret": clientSecret,
            "grant_type": "refresh_token"
        ]

        let bodyString = refreshParams.map { "\($0.key)=\($0.value)" }.joined(separator: "&")

        let curlCommand = """
        curl -s -X POST '\(GoogleOAuthConfig.tokenUrl)' \
            -H 'Content-Type: application/x-www-form-urlencoded' \
            -d '\(bodyString)'
        """

        DispatchQueue.global(qos: .userInitiated).async { [weak self] in
            let result = runShellCommand(curlCommand, timeout: 30)

            DispatchQueue.main.async {
                guard result.success,
                      let data = result.output.data(using: .utf8),
                      let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
                      let accessToken = json["access_token"] as? String,
                      let expiresIn = json["expires_in"] as? Int else {
                    logError("Failed to refresh token")
                    self?.status = .needsAuth
                    self?.onAuthStatusChanged?(self?.status ?? .needsAuth)
                    completion(false)
                    return
                }

                let newToken = OAuthToken(
                    accessToken: accessToken,
                    refreshToken: currentToken.refreshToken,
                    expiresIn: expiresIn,
                    tokenType: json["token_type"] as? String ?? "Bearer",
                    scope: json["scope"] as? String ?? currentToken.scope,
                    obtainedAt: Date()
                )

                self?.saveToken(newToken)
                self?.updateStatus()
                logInfo("Token refreshed successfully")
                completion(true)
            }
        }
    }

    // MARK: - API Access

    func getAccessToken(completion: @escaping (String?) -> Void) {
        guard let token = token else {
            completion(nil)
            return
        }

        if token.isExpired {
            refreshAccessToken { [weak self] success in
                completion(success ? self?.token?.accessToken : nil)
            }
        } else {
            completion(token.accessToken)
        }
    }

    // MARK: - Logout

    func logout() {
        token = nil
        try? FileManager.default.removeItem(atPath: Paths.tokenPath)
        updateStatus()
        logInfo("Logged out")
    }

    // MARK: - Setup Instructions

    func openSetupInstructions() {
        let alert = NSAlert()
        alert.messageText = "Google API Setup Required"
        alert.informativeText = """
        To use Google Media Backup, you need to:

        1. Go to Google Cloud Console
        2. Create a new project
        3. Enable Google Drive API and Photos Library API
        4. Create OAuth 2.0 credentials (Desktop app)
        5. Download the credentials JSON file
        6. Save it as:
           ~/.config/google-media-backup/credentials.json

        Click "Open Console" to get started.
        """
        alert.alertStyle = .informational
        alert.addButton(withTitle: "Open Console")
        alert.addButton(withTitle: "Open Config Folder")
        alert.addButton(withTitle: "Cancel")

        let response = alert.runModal()

        if response == .alertFirstButtonReturn {
            if let url = URL(string: "https://console.cloud.google.com/apis/credentials") {
                NSWorkspace.shared.open(url)
            }
        } else if response == .alertSecondButtonReturn {
            try? FileManager.default.createDirectory(atPath: Paths.configDir, withIntermediateDirectories: true)
            NSWorkspace.shared.open(URL(fileURLWithPath: Paths.configDir))
        }
    }
}
