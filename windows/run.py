"""
Main entry point for Google Media Backup Windows application.
"""

import sys
import os
import json
import traceback
from pathlib import Path
from datetime import datetime

# Add src to path
script_dir = Path(__file__).parent
sys.path.insert(0, str(script_dir / "src"))

# Set up startup logging
appdata = os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming")
log_dir = Path(appdata) / "GoogleMediaBackup"
log_dir.mkdir(parents=True, exist_ok=True)
startup_log = log_dir / "startup.log"

def log(message):
    """Write to startup log with timestamp."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    line = f"[{timestamp}] run.py: {message}\n"
    try:
        with open(startup_log, "a", encoding="utf-8") as f:
            f.write(line)
    except Exception:
        pass
    print(f"{timestamp} {message}")


def is_setup_complete() -> bool:
    """Check if setup has been completed."""
    setup_file = log_dir / "setup_complete.json"
    return setup_file.exists()


def run_setup():
    """Run the setup script with a visible console."""
    import subprocess

    setup_script = script_dir / "setup.py"

    # Use python.exe (not pythonw.exe) so the console is visible
    python_exe = sys.executable
    if python_exe.lower().endswith("pythonw.exe"):
        python_exe = python_exe[:-5] + ".exe"  # pythonw.exe -> python.exe

    subprocess.run([python_exe, str(setup_script)])


def main():
    """Main entry point."""
    log("main() started")

    # Check if setup is needed
    log(f"Checking setup status...")
    if not is_setup_complete():
        log("First run detected. Running setup...")
        run_setup()

        # Check again after setup
        if not is_setup_complete():
            log("Setup was not completed. Please run SETUP.bat")
            sys.exit(1)

    log("Setup is complete, starting app...")

    # Import and run the app
    try:
        log("Importing app module...")
        from app import get_app

        log("Creating app instance...")
        app = get_app()

        log("Calling app.run()...")
        app.run()

        log("app.run() returned normally")

    except ImportError as e:
        log(f"IMPORT ERROR: {e}\n{traceback.format_exc()}")
        print("Try running SETUP.bat to install dependencies.")
        sys.exit(1)
    except Exception as e:
        log(f"CRASH: {type(e).__name__}: {e}\n{traceback.format_exc()}")

        # Write to crash log
        crash_log = log_dir / "crash.log"
        with open(crash_log, "a", encoding="utf-8") as f:
            f.write(f"\n{'=' * 50}\n")
            f.write(f"Crash at: {datetime.now().isoformat()}\n")
            f.write(f"{type(e).__name__}: {e}\n")
            f.write(traceback.format_exc())

        sys.exit(1)


if __name__ == "__main__":
    main()
