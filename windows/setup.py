"""
Fully automated setup script for Google Media Backup Windows application.
Installs all dependencies and creates desktop shortcut automatically.
"""

import os
import sys
import json
import subprocess
import shutil
import ctypes
import urllib.request
from pathlib import Path


def is_admin():
    """Check if running with admin privileges."""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except Exception:
        return False


def print_header():
    """Print setup header."""
    print()
    print("=" * 60)
    print("  Google Media Backup - Windows Setup")
    print("=" * 60)
    print()


def print_step(step: int, message: str):
    """Print a setup step."""
    print(f"[{step}/6] {message}")


def check_python_version():
    """Check if Python version is 3.10 or higher."""
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 10):
        print(f"  ERROR: Python 3.10+ required, found {version.major}.{version.minor}")
        return False
    print(f"  Python {version.major}.{version.minor}.{version.micro} - OK")
    return True


def install_dependencies():
    """Install Python dependencies from requirements.txt."""
    script_dir = Path(__file__).parent
    requirements_file = script_dir / "requirements.txt"

    if not requirements_file.exists():
        print(f"  ERROR: requirements.txt not found")
        return False

    try:
        # Upgrade pip first
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "--upgrade", "pip"],
            capture_output=True,
            check=False
        )

        # Install requirements
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "-r", str(requirements_file), "-q"],
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            print(f"  Warning: Some packages may have issues: {result.stderr[:200]}")

        print("  Dependencies installed - OK")
        return True

    except Exception as e:
        print(f"  ERROR: {e}")
        return False


def check_ffmpeg():
    """Check if ffmpeg is available, offer to install via winget."""
    if shutil.which("ffmpeg"):
        print("  ffmpeg found - OK")
        return True

    print("  ffmpeg not found - attempting to install...")

    # Try winget first
    try:
        result = subprocess.run(
            ["winget", "install", "FFmpeg", "-e", "--silent", "--accept-package-agreements"],
            capture_output=True,
            text=True,
            timeout=300
        )
        if result.returncode == 0:
            print("  ffmpeg installed via winget - OK")
            return True
    except Exception:
        pass

    # If winget fails, provide instructions
    print("  WARNING: ffmpeg not installed (needed for video transcription)")
    print("  Install manually: https://ffmpeg.org/download.html")
    print("  Or run: winget install FFmpeg")
    return False  # Non-critical, continue setup


def create_config_directory():
    """Create the configuration directory."""
    appdata = os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming")
    config_dir = Path(appdata) / "GoogleMediaBackup"
    state_dir = config_dir / "state"

    try:
        config_dir.mkdir(parents=True, exist_ok=True)
        state_dir.mkdir(parents=True, exist_ok=True)
        print(f"  Config directory created - OK")
        return config_dir
    except Exception as e:
        print(f"  ERROR: {e}")
        return None


def create_desktop_shortcut():
    """Create a desktop shortcut to launch the app."""
    script_dir = Path(__file__).parent
    desktop = Path.home() / "Desktop"

    # Find pythonw.exe (windowless Python)
    pythonw_path = Path(sys.executable).parent / "pythonw.exe"
    if not pythonw_path.exists():
        # Fallback to python.exe if pythonw doesn't exist
        pythonw_path = Path(sys.executable)

    run_pyw_path = script_dir / "run.pyw"

    # Create a VBScript launcher (runs without any console window)
    launcher_path = script_dir / "GoogleMediaBackup.vbs"
    launcher_content = f'''Set WshShell = CreateObject("WScript.Shell")
WshShell.CurrentDirectory = "{script_dir}"
WshShell.Run """{pythonw_path}"" ""{run_pyw_path}""", 0, False
'''

    try:
        with open(launcher_path, "w") as f:
            f.write(launcher_content)

        # Create shortcut using PowerShell
        shortcut_path = desktop / "Google Media Backup.lnk"
        icon_path = script_dir / "resources" / "icon.ico"

        # PowerShell command to create shortcut
        ps_script = f'''
$WshShell = New-Object -ComObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut("{shortcut_path}")
$Shortcut.TargetPath = "wscript.exe"
$Shortcut.Arguments = '"{launcher_path}"'
$Shortcut.WorkingDirectory = "{script_dir}"
$Shortcut.Description = "Google Media Backup"
$Shortcut.WindowStyle = 1
'''
        # Add icon if it exists
        if icon_path.exists():
            ps_script += f'$Shortcut.IconLocation = "{icon_path}"\n'

        ps_script += '$Shortcut.Save()'

        result = subprocess.run(
            ["powershell", "-ExecutionPolicy", "Bypass", "-Command", ps_script],
            capture_output=True,
            text=True
        )

        if result.returncode == 0 or shortcut_path.exists():
            print(f"  Desktop shortcut created - OK")
            return True
        else:
            print(f"  Warning: Could not create shortcut: {result.stderr[:100]}")
            return False

    except Exception as e:
        print(f"  Warning: Could not create shortcut: {e}")
        return False


def create_app_icon():
    """Create a simple app icon if none exists."""
    script_dir = Path(__file__).parent
    resources_dir = script_dir / "resources"
    icon_path = resources_dir / "icon.ico"

    if icon_path.exists():
        return True

    try:
        resources_dir.mkdir(parents=True, exist_ok=True)

        # Try to use PIL to create a simple icon
        try:
            from PIL import Image, ImageDraw

            # Create a simple cloud icon
            size = 256
            img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
            draw = ImageDraw.Draw(img)

            # Blue cloud shape
            color = (66, 133, 244, 255)
            # Draw overlapping circles for cloud effect
            draw.ellipse([40, 100, 140, 200], fill=color)
            draw.ellipse([100, 80, 220, 200], fill=color)
            draw.ellipse([160, 100, 240, 200], fill=color)
            draw.rectangle([60, 140, 220, 200], fill=color)

            # Save as ICO with multiple sizes
            img.save(icon_path, format="ICO", sizes=[(16, 16), (32, 32), (48, 48), (256, 256)])
            print("  App icon created - OK")
            return True

        except ImportError:
            # PIL not available yet, will be created after dependencies install
            pass

    except Exception:
        pass

    return False


def mark_setup_complete():
    """Mark setup as complete."""
    appdata = os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming")
    setup_file = Path(appdata) / "GoogleMediaBackup" / "setup_complete.json"

    try:
        with open(setup_file, "w") as f:
            json.dump({
                "setup_complete": True,
                "version": "1.0.0",
                "python_path": sys.executable
            }, f, indent=2)
        return True
    except Exception:
        return False


def show_credentials_info(config_dir):
    """Show information about setting up Google credentials."""
    print()
    print("-" * 60)
    print("IMPORTANT: Google API Setup Required")
    print("-" * 60)
    print()
    print("To use Google Media Backup, you need Google OAuth credentials:")
    print()
    print("1. Go to: https://console.cloud.google.com/")
    print("2. Create a new project (or select existing)")
    print("3. Go to 'APIs & Services' > 'Enable APIs'")
    print("4. Enable 'Google Drive API' and 'Photos Library API'")
    print("5. Go to 'APIs & Services' > 'Credentials'")
    print("6. Create OAuth 2.0 credentials (Desktop application)")
    print("7. Download the JSON file")
    print(f"8. Save it as: {config_dir}\\credentials.json")
    print()


def main():
    """Main setup function."""
    print_header()

    # Step 1: Check Python
    print_step(1, "Checking Python version...")
    if not check_python_version():
        print("\nSetup failed. Please install Python 3.10 or later.")
        input("\nPress Enter to exit...")
        return 1

    # Step 2: Install dependencies
    print_step(2, "Installing Python dependencies...")
    if not install_dependencies():
        print("\nFailed to install dependencies.")
        input("\nPress Enter to exit...")
        return 1

    # Step 3: Check/install ffmpeg
    print_step(3, "Checking ffmpeg...")
    check_ffmpeg()  # Non-critical

    # Step 4: Create config directory
    print_step(4, "Creating configuration directory...")
    config_dir = create_config_directory()
    if not config_dir:
        print("\nFailed to create config directory.")
        input("\nPress Enter to exit...")
        return 1

    # Step 5: Create app icon
    print_step(5, "Creating application icon...")
    create_app_icon()

    # Step 6: Create desktop shortcut
    print_step(6, "Creating desktop shortcut...")
    create_desktop_shortcut()

    # Mark complete
    mark_setup_complete()

    # Show success and credentials info
    print()
    print("=" * 60)
    print("  Setup Complete!")
    print("=" * 60)

    # Check if credentials exist
    creds_file = config_dir / "credentials.json"
    if not creds_file.exists():
        show_credentials_info(config_dir)
    else:
        print()
        print("Google credentials found. You're ready to go!")
        print()

    print("To start the app:")
    print("  Double-click 'Google Media Backup' on your desktop")
    print()

    input("Press Enter to exit...")
    return 0


if __name__ == "__main__":
    sys.exit(main())
