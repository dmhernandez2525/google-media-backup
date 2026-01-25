# Google Media Backup

A native macOS menu bar app that downloads videos and documents from Google Drive and Google Photos, then transcribes all videos locally using Whisper AI.

## Features

- **Google Drive Integration**: Downloads videos and documents (PDFs, Google Docs, Sheets, Slides)
- **Google Photos Integration**: Downloads videos from your Photos library
- **Local Transcription**: Uses whisper-cpp to transcribe videos locally (no API costs)
- **Menu Bar App**: Runs in the background with a clean status bar interface
- **State Management**: Tracks download and transcription status, resumes from where it left off
- **Auto-sync**: Option to automatically download on app launch
- **Auto-transcribe**: Option to automatically transcribe videos after download

## Requirements

- macOS 12.0 or later
- Homebrew (for dependencies)
- Google Cloud project with OAuth credentials

## Installation

### 1. Install Dependencies

```bash
# Install whisper-cpp for transcription
brew install whisper-cpp

# Install ffmpeg for audio extraction
brew install ffmpeg
```

### 2. Setup Google Cloud Credentials

1. Go to [Google Cloud Console](https://console.cloud.google.com/apis/credentials)
2. Create a new project (or select existing)
3. Enable the following APIs:
   - Google Drive API
   - Photos Library API
4. Create OAuth 2.0 credentials:
   - Click "Create Credentials" > "OAuth client ID"
   - Select "Desktop app"
   - Download the JSON file
5. Save the credentials:
   ```bash
   mkdir -p ~/.config/google-media-backup
   mv ~/Downloads/client_secret_*.json ~/.config/google-media-backup/credentials.json
   ```

### 3. Build the App

```bash
cd GoogleMediaBackup
./build.sh
```

The app will be created at `~/Desktop/Google Media Backup.app`

### 4. First Run

1. Double-click the app on your Desktop
2. Click the cloud icon in the menu bar
3. Click "Sign In" and authorize with Google
4. Start downloading!

## Usage

### Menu Bar

Click the cloud icon in the menu bar to access:

- **Start Download**: Begin downloading from Drive and Photos
- **Transcribe Videos**: Transcribe all downloaded videos
- **Open Downloads Folder**: Open the download directory
- **Show Panel**: Open the full management panel
- **Preferences**: Configure settings

### Main Panel

The main panel (accessible via "Show Panel") provides:

- **Home**: Status overview, statistics, quick actions
- **Downloads**: List of all downloaded files with status
- **Transcriptions**: Transcription status and controls

### Preferences

Configure:

- Download location
- What to download (videos, documents, photos)
- Auto-download on launch
- Auto-transcribe after download
- Whisper model selection

## File Organization

Downloaded files are organized as:

```
~/Desktop/Google Media Backup/
├── Videos/
│   ├── Drive/          # Videos from Google Drive
│   └── Photos/         # Videos from Google Photos
└── Documents/          # PDFs and exported Google Docs
```

Transcripts are saved alongside videos with `.txt` extension.

## Whisper Models

Available transcription models:

| Model | Size | Speed | Accuracy |
|-------|------|-------|----------|
| tiny | 75MB | Fastest | Basic |
| base | 150MB | Fast | Good |
| small | 500MB | Moderate | Recommended |
| medium | 1.5GB | Slow | Best |

Download models via Preferences > Download Model.

## Configuration Files

All configuration is stored in `~/.config/google-media-backup/`:

- `config.json` - App settings
- `credentials.json` - Google OAuth credentials (you provide)
- `token.json` - OAuth token (created after sign-in)
- `state/` - Download and transcription state

## Building from Source

Requirements:
- Xcode Command Line Tools
- Swift 5.5+

```bash
cd GoogleMediaBackup
./build.sh
```

## Troubleshooting

### "Sign in required" after restart
Your OAuth token may have expired. Click Sign In again.

### "whisper-cpp not installed"
Run: `brew install whisper-cpp`

### "Model not downloaded"
Open Preferences and click "Download Model".

### Downloads are slow
Google APIs have rate limits. The app respects these limits to avoid blocking.

## Privacy

- All data is stored locally on your machine
- Transcription happens locally using whisper-cpp
- OAuth tokens are stored securely in your config directory
- No data is sent to third parties

## License

MIT License
