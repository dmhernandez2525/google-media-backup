# Google Media Backup - Windows

Windows version of the Google Media Backup application. Backs up videos and documents from Google Drive and Google Photos, with automatic video transcription using Whisper AI.

## Features

- **Google Drive Integration**: Download videos and documents, export Google Docs/Sheets/Slides
- **Google Photos Integration**: Download all videos from your Photos library
- **Automatic Transcription**: Transcribe videos locally using Whisper AI (no cloud costs)
- **System Tray**: Background app with quick access menu
- **Pause/Resume**: Pause and resume downloads at any time
- **State Persistence**: Picks up where it left off after restarts

## Requirements

- Python 3.10 or later
- Windows 10/11
- FFmpeg (for video transcription)
- Google Cloud OAuth credentials

## Installation

1. **Run Setup**:
   ```
   Double-click SETUP.bat
   ```

2. **Get Google Credentials**:
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Create a project and enable:
     - Google Drive API
     - Google Photos Library API
   - Create OAuth 2.0 credentials (Desktop application)
   - Download the JSON file
   - Save as: `%APPDATA%\GoogleMediaBackup\credentials.json`

3. **Install FFmpeg** (for transcription):
   ```
   winget install FFmpeg
   ```

## Usage

1. **Launch**: Double-click "Google Media Backup" on your desktop, or run `python run.py`

2. **Sign In**: Click "Sign In" from the system tray menu

3. **Download**: Click "Start Download" to scan and download your media

4. **Transcribe**: Videos are automatically transcribed after download (configurable)

## Configuration

Settings are stored in `%APPDATA%\GoogleMediaBackup\config.json`:

| Setting | Description | Default |
|---------|-------------|---------|
| download_path | Where to save files | `Desktop\Google Media Backup` |
| auto_download | Download on startup | false |
| auto_transcribe | Transcribe after download | true |
| transcription_model | Whisper model size | small |
| download_videos | Download video files | true |
| download_documents | Download documents | true |
| download_photos | Download from Photos | true |

## File Structure

```
%USERPROFILE%\Desktop\Google Media Backup\
├── Videos\
│   ├── Drive\          # Videos from Google Drive
│   └── Photos\         # Videos from Google Photos
└── Documents\          # Documents from Google Drive
```

## Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run the app
python run.py

# Run without console
pythonw run.pyw
```

## Troubleshooting

**"Credentials not found"**
- Ensure `credentials.json` is in `%APPDATA%\GoogleMediaBackup\`

**"FFmpeg not found"**
- Install FFmpeg and ensure it's in your PATH

**Downloads fail**
- Check your internet connection
- Verify OAuth credentials are valid
- Try signing out and back in

## macOS Version

The macOS version is located in the `../macos/` directory and is built with Swift/Cocoa.
