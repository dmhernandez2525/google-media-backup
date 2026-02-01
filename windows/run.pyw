"""
Windows launcher for Google Media Backup (no console window).
"""

import sys
import os
import traceback
from pathlib import Path
from datetime import datetime

# Set up early logging before anything else
script_dir = Path(__file__).parent
appdata = os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming")
log_dir = Path(appdata) / "GoogleMediaBackup"
log_dir.mkdir(parents=True, exist_ok=True)
startup_log = log_dir / "startup.log"

def log(message):
    """Write to startup log with timestamp."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    line = f"[{timestamp}] {message}\n"
    with open(startup_log, "a", encoding="utf-8") as f:
        f.write(line)

# Clear old startup log and start fresh
with open(startup_log, "w", encoding="utf-8") as f:
    f.write(f"=== Google Media Backup Startup Log ===\n")
    f.write(f"Started: {datetime.now().isoformat()}\n")
    f.write(f"Python: {sys.executable}\n")
    f.write(f"Version: {sys.version}\n")
    f.write(f"Script: {__file__}\n")
    f.write(f"Working Dir: {os.getcwd()}\n")
    f.write(f"=" * 50 + "\n\n")

try:
    log("Adding src to path...")
    sys.path.insert(0, str(script_dir / "src"))
    log(f"sys.path: {sys.path[:3]}")

    log("Importing run module...")
    from run import main

    log("Calling main()...")
    main()

    log("main() returned normally")

except Exception as e:
    error_msg = f"CRASH: {type(e).__name__}: {e}\n{traceback.format_exc()}"
    log(error_msg)

    # Also write to a crash log
    crash_log = log_dir / "crash.log"
    with open(crash_log, "a", encoding="utf-8") as f:
        f.write(f"\n{'=' * 50}\n")
        f.write(f"Crash at: {datetime.now().isoformat()}\n")
        f.write(error_msg)

    # Show error in a message box since there's no console
    import ctypes
    ctypes.windll.user32.MessageBoxW(
        0,
        f"Failed to start Google Media Backup:\n\n{e}\n\nCheck log at:\n{startup_log}",
        "Google Media Backup - Error",
        0x10  # MB_ICONERROR
    )
