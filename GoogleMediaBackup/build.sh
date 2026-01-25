#!/bin/zsh
# Build Google Media Backup menubar app

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
APP_NAME="Google Media Backup"
APP_PATH="$HOME/Desktop/${APP_NAME}.app"
BUILD_DIR="$SCRIPT_DIR/build"
SOURCES_DIR="$SCRIPT_DIR/Sources"

echo "Building Google Media Backup..."

# Clean previous build
rm -rf "$BUILD_DIR"
rm -rf "$APP_PATH"
mkdir -p "$BUILD_DIR"

# Collect all Swift source files
SWIFT_FILES=(
    "$SOURCES_DIR/Utils.swift"
    "$SOURCES_DIR/Config.swift"
    "$SOURCES_DIR/GoogleAuthManager.swift"
    "$SOURCES_DIR/DriveClient.swift"
    "$SOURCES_DIR/PhotosClient.swift"
    "$SOURCES_DIR/TranscriptionManager.swift"
    "$SOURCES_DIR/DownloadManager.swift"
    "$SOURCES_DIR/Windows/ProgressWindow.swift"
    "$SOURCES_DIR/Windows/ConfigWindow.swift"
    "$SOURCES_DIR/Windows/MainPanel.swift"
    "$SOURCES_DIR/AppDelegate.swift"
    "$SOURCES_DIR/main.swift"
)

echo "Compiling ${#SWIFT_FILES[@]} source files..."

# Compile Swift
swiftc -o "$BUILD_DIR/GoogleMediaBackup" \
    -O \
    -target arm64-apple-macosx12.0 \
    -sdk $(xcrun --show-sdk-path) \
    -framework Cocoa \
    "${SWIFT_FILES[@]}"

echo "Creating app bundle..."

# Create app bundle structure
mkdir -p "$APP_PATH/Contents/MacOS"
mkdir -p "$APP_PATH/Contents/Resources"

# Copy executable
cp "$BUILD_DIR/GoogleMediaBackup" "$APP_PATH/Contents/MacOS/"

# Create Info.plist
cat > "$APP_PATH/Contents/Info.plist" << 'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleExecutable</key>
    <string>GoogleMediaBackup</string>
    <key>CFBundleIdentifier</key>
    <string>com.google-media-backup.menubar</string>
    <key>CFBundleName</key>
    <string>Google Media Backup</string>
    <key>CFBundleDisplayName</key>
    <string>Google Media Backup</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>CFBundleVersion</key>
    <string>1.0</string>
    <key>CFBundleShortVersionString</key>
    <string>1.0</string>
    <key>CFBundleIconFile</key>
    <string>AppIcon</string>
    <key>LSMinimumSystemVersion</key>
    <string>12.0</string>
    <key>LSUIElement</key>
    <true/>
    <key>NSHighResolutionCapable</key>
    <true/>
    <key>LSApplicationCategoryType</key>
    <string>public.app-category.utilities</string>
</dict>
</plist>
EOF

# Create icon from iconset if exists
echo "Building app icon..."
if [ -d "$SCRIPT_DIR/AppIcon.iconset" ] && [ "$(ls -A $SCRIPT_DIR/AppIcon.iconset 2>/dev/null)" ]; then
    iconutil -c icns "$SCRIPT_DIR/AppIcon.iconset" -o "$APP_PATH/Contents/Resources/AppIcon.icns" 2>/dev/null || echo "  (using system default icon)"
elif [ -f "$SCRIPT_DIR/AppIcon.icns" ]; then
    cp "$SCRIPT_DIR/AppIcon.icns" "$APP_PATH/Contents/Resources/"
else
    echo "  (using system default icon)"
fi

# Touch the app to refresh icon cache
touch "$APP_PATH"

echo ""
echo "Build successful!"
echo "   App created at: $APP_PATH"
echo ""
echo "Setup:"
echo "  1. Go to https://console.cloud.google.com/apis/credentials"
echo "  2. Create OAuth 2.0 credentials (Desktop app)"
echo "  3. Enable Google Drive API and Photos Library API"
echo "  4. Download credentials and save as:"
echo "     ~/.config/google-media-backup/credentials.json"
echo ""
echo "To add to Login Items (auto-start):"
echo "  System Settings > General > Login Items > Add '$APP_NAME'"
