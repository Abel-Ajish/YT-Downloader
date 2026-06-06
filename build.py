import subprocess
import os
import sys
import shutil

def run_command(command):
    print(f"Running: {command}")
    process = subprocess.Popen(command, shell=True)
    process.wait()
    if process.returncode != 0:
        print(f"Error: Command failed with exit code {process.returncode}")
        sys.exit(1)

def build():
    # 1. Verification Step: Ensure all required files exist
    required_files = ['download.pyw', 'installer.py', 'uninstaller.py', 'YT-Downloader.spec', 'Setup.spec']
    missing_files = [f for f in required_files if not os.path.exists(f)]
    if missing_files:
        print(f"Error: Missing required files for build: {', '.join(missing_files)}")
        sys.exit(1)

    # 2. Ensure output directories are clean
    for folder in ['build', 'dist']:
        if os.path.exists(folder):
            try:
                shutil.rmtree(folder)
            except Exception as e:
                print(f"Warning: Could not clean {folder} folder: {e}")

    print("--- Starting Production Build Process ---")

    # 2. Build the Main Application
    print("\nBuilding Main Application (YT-Downloader.exe)...")
    run_command("pyinstaller --noconfirm YT-Downloader.spec")

    # 3. Build the Uninstaller
    print("\nBuilding Uninstaller (uninstaller.exe)...")
    # We'll create a simple spec for the uninstaller on the fly or use a direct command
    run_command("pyinstaller --noconfirm --onefile --windowed --name uninstaller uninstaller.py")

    # 4. Build the Bootstrap Installer
    print("\nBuilding Bootstrap Installer (Setup-YTDownloader.exe)...")
    run_command("pyinstaller --noconfirm Setup.spec")

    print("\n--- Build Complete! ---")
    print("Files available in the 'dist' folder:")
    print(" - YT-Downloader.exe (Standalone App)")
    print(" - uninstaller.exe (Uninstaller Tool)")
    print(" - Setup-YTDownloader.exe (Main Installer to upload to GitHub)")

if __name__ == "__main__":
    # Check for pyinstaller
    try:
        import PyInstaller
    except ImportError:
        print("Error: PyInstaller is not installed. Run 'pip install pyinstaller' first.")
        sys.exit(1)
        
    build()
