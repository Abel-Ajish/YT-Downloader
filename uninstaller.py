import os
import shutil
import platform
import subprocess
import tkinter as tk
from tkinter import messagebox
from pathlib import Path

def remove_shortcuts():
    """Remove desktop and start menu shortcuts on Windows."""
    if platform.system() == "Windows":
        desktop = Path(os.path.expanduser("~/Desktop"))
        shortcut_name = "YT-Downloader.lnk"
        shortcut_path = desktop / shortcut_name
        if shortcut_path.exists():
            os.remove(shortcut_path)

def run_uninstaller():
    root = tk.Tk()
    root.withdraw()
    
    confirm = messagebox.askyesno("Confirm Uninstall", "Are you sure you want to completely remove YT-Downloader and all its components?")
    
    if confirm:
        try:
            # 1. Remove Shortcuts
            remove_shortcuts()
            
            # 2. Identify install directory (assuming Local AppData for non-admin install)
            install_dir = Path(os.getenv("LOCALAPPDATA")) / "YTDownloader"
            
            # 3. Identify settings directory
            settings_dir = Path.home() / ".yt_downloader"
            
            remove_settings = messagebox.askyesno("Remove Data", "Do you also want to remove your settings and logs?")
            
            if install_dir.exists():
                # We can't delete the uninstaller if it's running from inside the directory
                # But if it's a temp file, we can.
                shutil.rmtree(install_dir, ignore_errors=True)
                
            if remove_settings and settings_dir.exists():
                shutil.rmtree(settings_dir, ignore_errors=True)
                
            messagebox.showinfo("Success", "YT-Downloader has been successfully removed from your computer.")
            
        except Exception as e:
            messagebox.showerror("Error", f"An error occurred during uninstallation: {str(e)}")
    
    root.destroy()

if __name__ == "__main__":
    run_uninstaller()
