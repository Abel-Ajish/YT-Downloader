import subprocess
import shutil
import platform
import os
import sys
import logging
from tkinter import messagebox

logger = logging.getLogger(__name__)

class DependencyManager:
    @staticmethod
    def is_ffmpeg_installed():
        """Check if FFmpeg is installed and accessible in the system PATH."""
        return shutil.which("ffmpeg") is not None

    @staticmethod
    def get_install_command():
        """Return the OS-appropriate command to install FFmpeg."""
        os_name = platform.system()
        if os_name == "Windows":
            # Check if winget is available
            if shutil.which("winget"):
                return "winget install ffmpeg"
            return None
        elif os_name == "Darwin": # macOS
            if shutil.which("brew"):
                return "brew install ffmpeg"
            return None
        elif os_name == "Linux":
            if shutil.which("apt"):
                return "sudo apt update && sudo apt install -y ffmpeg"
            elif shutil.which("dnf"):
                return "sudo dnf install -y ffmpeg"
            elif shutil.which("pacman"):
                return "sudo pacman -S ffmpeg"
            return None
        return None

    @classmethod
    def install_ffmpeg(cls):
        """Attempt to install FFmpeg based on the operating system."""
        command = cls.get_install_command()
        if not command:
            logger.error("No automated installation method found for this OS.")
            return False, "No automated installation method found. Please install FFmpeg manually."

        try:
            logger.info(f"Executing installation command: {command}")
            # On Windows, winget might need to be run in a shell
            # On Linux/macOS, we might need shell=True for sudo or brew
            process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            stdout, stderr = process.communicate()
            
            if process.returncode == 0:
                logger.info("FFmpeg installed successfully.")
                return True, "FFmpeg installed successfully!"
            else:
                logger.error(f"FFmpeg installation failed: {stderr}")
                return False, f"Installation failed: {stderr}"
        except Exception as e:
            logger.exception("An error occurred during FFmpeg installation.")
            return False, str(e)

def check_dependencies(parent_window=None):
    """
    Main entry point for dependency validation.
    Returns True if all dependencies are met, False otherwise.
    """
    if not DependencyManager.is_ffmpeg_installed():
        msg = ("FFmpeg is missing, which is required for high-quality video merging and audio conversion.\n\n"
               "Would you like to attempt an automated installation?")
        
        if messagebox.askyesno("Missing Dependency", msg, parent=parent_window):
            success, message = DependencyManager.install_ffmpeg()
            if success:
                messagebox.showinfo("Success", message, parent=parent_window)
                return True
            else:
                error_msg = f"Automated installation failed:\n{message}\n\nPlease install FFmpeg manually to use all features."
                messagebox.showerror("Error", error_msg, parent=parent_window)
                return False
        else:
            messagebox.showwarning("Warning", "Some features may not work correctly without FFmpeg.", parent=parent_window)
            return True # Let the user proceed at their own risk
    return True
