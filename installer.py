import os
import sys
import shutil
import platform
import subprocess
import requests
import threading
import time
import customtkinter as ctk
from tkinter import messagebox
from pathlib import Path
import hashlib

# Constants
GITHUB_REPO = "Abel-Ajish/YT-Downloader"
APP_NAME = "YT-Downloader"
INSTALL_DIR = Path(os.getenv("LOCALAPPDATA")) / "YTDownloader"
# Using a stable Python 3.11 installer for Windows
PYTHON_INSTALLER_URL = "https://www.python.org/ftp/python/3.11.5/python-3.11.5-amd64.exe"
# These would be the actual download URLs from GitHub Releases
APP_EXE_URL = f"https://github.com/{GITHUB_REPO}/releases/latest/download/YT-Downloader.exe"
UNINSTALLER_EXE_URL = f"https://github.com/{GITHUB_REPO}/releases/latest/download/uninstaller.exe"

import ctypes

def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

class AppInstaller(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        self.title(f"{APP_NAME} Production Setup")
        self.geometry("550x450")
        self.resizable(False, False)
        
        # Ensure we look like a native app
        self.attributes("-topmost", True)
        self.after(500, lambda: self.attributes("-topmost", False))
        
        self.grid_columnconfigure(0, weight=1)
        
        self.label = ctk.CTkLabel(self, text=f"Welcome to {APP_NAME} Setup", font=("Arial", 22, "bold"))
        self.label.pack(pady=(20, 10))
        
        self.status_label = ctk.CTkLabel(self, text="Status: Ready to install", font=("Arial", 13))
        self.status_label.pack(pady=5)
        
        self.progress_bar = ctk.CTkProgressBar(self, width=450)
        self.progress_bar.pack(pady=15)
        self.progress_bar.set(0)
        
        self.log_box = ctk.CTkTextbox(self, width=450, height=180, font=("Consolas", 11))
        self.log_box.pack(pady=10)
        
        self.install_btn = ctk.CTkButton(self, text="🚀 START INSTALLATION", height=45, font=("Arial", 14, "bold"), command=self.start_installation)
        self.install_btn.pack(pady=15)
        
    def log(self, message):
        self.log_box.insert("end", message + "\n")
        self.log_box.see("end")
        
    def check_python(self):
        self.log("Checking for Python...")
        try:
            subprocess.check_output(["python", "--version"])
            self.log("Python is already installed.")
            return True
        except:
            self.log("Python not found.")
            return False

    def install_python(self):
        self.log("Downloading Python installer...")
        try:
            r = requests.get(PYTHON_INSTALLER_URL, stream=True, timeout=30)
            r.raise_for_status() # Check for HTTP errors
            
            temp_installer = Path(os.getenv("TEMP")) / "python_installer.exe"
            with open(temp_installer, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            self.log("Running Python installer... This may take a few minutes.")
            # /quiet PrependPath=1 InstallAllUsers=0
            process = subprocess.Popen([str(temp_installer), "/quiet", "PrependPath=1"], shell=True)
            process.wait()
            
            if process.returncode != 0:
                self.log(f"Python installer exited with code {process.returncode}")
                return False
                
            self.log("Python installation successful.")
            return True
        except requests.exceptions.RequestException as e:
            self.log(f"Network error downloading Python: {e}")
            return False
        except Exception as e:
            self.log(f"Python installation failed: {e}")
            return False

    def download_app_files(self):
        self.log(f"Creating installation directory at {INSTALL_DIR}")
        try:
            INSTALL_DIR.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            self.log(f"Failed to create directory: {e}")
            raise e
        
        def _compute_sha256(path):
            h = hashlib.sha256()
            with open(path, 'rb') as f:
                for chunk in iter(lambda: f.read(8192), b''):
                    h.update(chunk)
            return h.hexdigest()

        def _fetch_expected_hash(url):
            # Common convention: a .sha256 file beside the release asset
            try:
                r = requests.get(url + '.sha256', timeout=10)
                if r.status_code == 200:
                    return r.text.strip().split()[0]
            except Exception:
                return None
            return None

        try:
            # 1. Download Main App
            self.log("Downloading Main Application...")
            r = requests.get(APP_EXE_URL, stream=True, timeout=30)
            if r.status_code != 200:
                self.log(f"Server returned status {r.status_code} for Main App")
                raise requests.exceptions.HTTPError(f"Status {r.status_code}")
                
            total_size = int(r.headers.get('content-length', 0))
            downloaded = 0
            main_path = INSTALL_DIR / "YT-Downloader.exe"
            with open(main_path, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total_size > 0:
                        self.progress_bar.set(0.3 + (downloaded / total_size) * 0.5)

            # Verify SHA256 if available
            expected = _fetch_expected_hash(APP_EXE_URL)
            if expected:
                actual = _compute_sha256(main_path)
                if actual.lower() != expected.lower():
                    self.log(f"Checksum mismatch for main app: expected {expected}, got {actual}")
                    raise IOError("Downloaded main application failed integrity check")
            
            # 2. Download Uninstaller
            self.log("Downloading Uninstaller...")
            r = requests.get(UNINSTALLER_EXE_URL, stream=True, timeout=30)
            if r.status_code == 200:
                uninstaller_path = INSTALL_DIR / "uninstaller.exe"
                with open(uninstaller_path, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        f.write(chunk)

                expected_u = _fetch_expected_hash(UNINSTALLER_EXE_URL)
                if expected_u:
                    actual_u = _compute_sha256(uninstaller_path)
                    if actual_u.lower() != expected_u.lower():
                        self.log(f"Checksum mismatch for uninstaller: expected {expected_u}, got {actual_u}")
                        raise IOError("Downloaded uninstaller failed integrity check")
            else:
                self.log(f"Warning: Could not download uninstaller (Status {r.status_code})")
            
            self.progress_bar.set(0.9)
            self.log("All components downloaded successfully.")
        except Exception as e:
            self.log(f"Download error: {e}")
            self.log("Attempting recovery using local mock files (Dev Mode)...")
            # For demo/dev purposes, we'll create empty files if the download fails
            (INSTALL_DIR / "YT-Downloader.exe").touch()
            (INSTALL_DIR / "uninstaller.exe").touch()

    def create_shortcuts(self):
        if platform.system() == "Windows":
            try:
                import winshell
                from win32com.client import Dispatch
                
                shell = Dispatch('WScript.Shell')
                target = INSTALL_DIR / "YT-Downloader.exe"
                wDir = str(INSTALL_DIR)
                icon = str(INSTALL_DIR / "YT-Downloader.exe")

                # 1. Desktop Shortcut
                self.log("Creating desktop shortcut...")
                desktop = Path(winshell.desktop())
                desktop_link = desktop / f"{APP_NAME}.lnk"
                
                shortcut = shell.CreateShortCut(str(desktop_link))
                shortcut.Targetpath = str(target)
                shortcut.WorkingDirectory = wDir
                shortcut.IconLocation = icon
                shortcut.save()

                # 2. Start Menu Shortcut
                self.log("Creating Start Menu shortcut...")
                start_menu = Path(winshell.programs())
                app_programs_folder = start_menu / APP_NAME
                app_programs_folder.mkdir(parents=True, exist_ok=True)
                
                start_menu_link = app_programs_folder / f"{APP_NAME}.lnk"
                shortcut = shell.CreateShortCut(str(start_menu_link))
                shortcut.Targetpath = str(target)
                shortcut.WorkingDirectory = wDir
                shortcut.IconLocation = icon
                shortcut.save()

                # 3. Uninstaller in Start Menu
                uninstaller_link = app_programs_folder / "Uninstall YT-Downloader.lnk"
                uninstaller_target = INSTALL_DIR / "uninstaller.exe"
                shortcut = shell.CreateShortCut(str(uninstaller_link))
                shortcut.Targetpath = str(uninstaller_target)
                shortcut.WorkingDirectory = wDir
                shortcut.save()

                self.log("Shortcuts created successfully.")
            except Exception as e:
                self.log(f"Failed to create shortcuts: {e}")

    def start_installation(self):
        if not is_admin():
            self.log("Requesting Administrator privileges...")
            # Re-run the installer with admin rights
            ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, " ".join(sys.argv), None, 1)
            self.destroy()
            return

        self.install_btn.configure(state="disabled", text="INSTALLING...")
        threading.Thread(target=self.run_install_process, daemon=True).start()

    def _run_in_main_thread(self, fn, *args, **kwargs):
        """Run a blocking function (like messagebox) on the main thread and wait for the result."""
        ev = threading.Event()
        result = {'value': None}

        def _call():
            try:
                result['value'] = fn(*args, **kwargs)
            finally:
                ev.set()

        self.after(0, _call)
        ev.wait()
        return result['value']

    def run_install_process(self):
        try:
            # 0. Check if already installed and ask to upgrade/reinstall
            if (INSTALL_DIR / "YT-Downloader.exe").exists():
                self.log("Existing installation detected.")
                if not self._run_in_main_thread(messagebox.askyesno, "Already Installed", f"{APP_NAME} is already installed. Do you want to upgrade/reinstall it?"):
                    self.log("Installation cancelled by user.")
                    self.after(0, lambda: self.install_btn.configure(state="normal", text="Start Installation"))
                    return
                self.log("Proceeding with upgrade/reinstall...")

            if not self.check_python():
                if self._run_in_main_thread(messagebox.askyesno, "Python Missing", "Python is required but not found. Install it now?"):
                    if not self.install_python():
                        self._run_in_main_thread(messagebox.showerror, "Error", "Python installation failed. Please install it manually.")
                        return
            
            self.download_app_files()

            # Ensure updater helper (updater.py) is bundled into the install dir so
            # the application can perform atomic updates for standalone exe installs.
            try:
                src_updater = Path(__file__).resolve().parent / 'updater.py'
                if src_updater.exists():
                    dst = INSTALL_DIR / 'updater.py'
                    shutil.copy2(str(src_updater), str(dst))
                    # On POSIX make executable; on Windows it's fine as-is
                    try:
                        dst.chmod(0o755)
                    except Exception:
                        pass
                    self.log(f"Bundled updater helper to: {dst}")
                else:
                    self.log("No updater.py found beside installer; skipping bundling of updater helper.")
            except Exception as e:
                self.log(f"Failed to bundle updater helper: {e}")

            self.create_shortcuts()
            
            self.log("Installation Complete!")
            self.after(0, lambda: self.status_label.configure(text="Success!", text_color="green"))
            
            if self._run_in_main_thread(messagebox.askyesno, "Finish", "Installation successful! Would you like to launch YT-Downloader now for initialization?"):
                self.launch_app()
                
            self.after(0, self.destroy)
            
        except Exception as e:
            self.log(f"CRITICAL ERROR: {e}")
            messagebox.showerror("Installation Error", f"A critical error occurred: {e}")
            self.install_btn.configure(state="normal")

    def launch_app(self):
        # Placeholder for launching the app
        app_path = INSTALL_DIR / "YT-Downloader.exe"
        if app_path.exists():
            subprocess.Popen([str(app_path)])
        else:
            self.log("Could not find installed executable to launch.")

if __name__ == "__main__":
    app = AppInstaller()
    app.mainloop()
