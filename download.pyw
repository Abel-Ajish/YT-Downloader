import customtkinter as ctk
import yt_dlp
import os
import subprocess
import platform
import threading
import time
import logging
import traceback
import requests
from PIL import Image
from io import BytesIO
from pathlib import Path
from tkinter import filedialog, messagebox

# Local imports
from logger_config import setup_logging
from dependency_manager import check_dependencies
from settings_manager import SettingsManager

# Initialize logging
logger = setup_logging()

# Constants
GITHUB_REPO = "Abel-Ajish/YT-Downloader"
VERSION = "v1.0.2"

class MegaDownloader(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Load Settings
        self.settings_mgr = SettingsManager()
        
        # Window Setup
        self.title("Youtube Audio/Video Downloader")
        geometry = self.settings_mgr.get("window_geometry")
        self.geometry(geometry)
        self.minsize(600, 700)
        self.resizable(True, True)

        # Apply Theme
        self.appearance_mode = self.settings_mgr.get("appearance_mode")
        ctk.set_appearance_mode(self.appearance_mode)
        ctk.set_default_color_theme("blue")

        # Variables
        self.save_dir = self.settings_mgr.get("save_dir")
        self.start_time = 0
        self.current_metadata_url = ""
        self.thumbnail_image = None

        # --- UI LAYOUT ---
        self._build_ui()
        
        # --- BINDINGS ---
        self.bind("<Control-s>", lambda e: self.trigger_download())
        self.bind("<Control-o>", lambda e: self.choose_folder())
        
        # --- INITIAL CHECKS ---
        self.after(100, self._initial_checks)

    def _initial_checks(self):
        """Perform first-run checks."""
        if not check_dependencies(self):
            logger.warning("Dependencies check failed or user opted out.")

    def _build_ui(self):
        # Header & Theme Toggle
        self.header_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.header_frame.pack(pady=(15, 5), fill="x", padx=40)
        
        self.title_lbl = ctk.CTkLabel(self.header_frame, text="Youtube Audio/Video Downloader", font=("Arial", 20, "bold"))
        self.title_lbl.pack(side="left")
        
        self.theme_switch = ctk.CTkSwitch(self.header_frame, text="Dark Mode", command=self.toggle_theme)
        if self.appearance_mode == "Dark":
            self.theme_switch.select()
        else:
            self.theme_switch.deselect()
        self.theme_switch.pack(side="right")

        # 1. URL Input Section
        self.url_label = ctk.CTkLabel(self, text="YouTube URL Link (Video, Short, Playlist, or Audio):", font=("Arial", 12, "bold"))
        self.url_label.pack(anchor="w", padx=40, pady=(10, 2))
        
        self.url_entry = ctk.CTkEntry(self, placeholder_text="https://www.youtube.com/watch?v=...")
        self.url_entry.pack(pady=5, padx=40, fill="x")
        self.url_entry.bind("<KeyRelease>", self.on_url_change)

        # 1.5 Metadata Preview Section
        self.preview_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.preview_frame.pack(pady=5, padx=40, fill="x")
        self.preview_frame.pack_forget() # Hide by default

        self.thumb_label = ctk.CTkLabel(self.preview_frame, text="", width=120, height=68)
        self.thumb_label.pack(side="left", padx=(0, 15))

        self.info_frame = ctk.CTkFrame(self.preview_frame, fg_color="transparent")
        self.info_frame.pack(side="left", fill="both", expand=True)

        self.video_title_lbl = ctk.CTkLabel(self.info_frame, text="Video Title", font=("Arial", 12, "bold"), anchor="w", wraplength=400)
        self.video_title_lbl.pack(fill="x")

        self.video_duration_lbl = ctk.CTkLabel(self.info_frame, text="Duration: 00:00", font=("Arial", 11), text_color="gray", anchor="w")
        self.video_duration_lbl.pack(fill="x")

        # 2. Storage Directory Configuration
        self.loc_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.loc_frame.pack(pady=10, fill="x", padx=40)
        
        display_path = self.save_dir
        if len(display_path) > 45:
            display_path = f"...{display_path[-45:]}"
            
        self.loc_label = ctk.CTkLabel(self.loc_frame, text=f"Save Folder: {display_path}", text_color="gray")
        self.loc_label.pack(side="left", fill="x", expand=True, anchor="w")
        
        self.open_folder_btn = ctk.CTkButton(self.loc_frame, text="📂 Open Folder", width=110, fg_color="#495057", hover_color="#343a40", command=self.quick_open_folder)
        self.open_folder_btn.pack(side="right", padx=(0, 10))
        
        self.loc_btn = ctk.CTkButton(self.loc_frame, text="Change Location", width=120, command=self.choose_folder)
        self.loc_btn.pack(side="right")

        # 3. Features & Settings Dashboard
        self.settings_frame = ctk.CTkFrame(self)
        self.settings_frame.pack(pady=15, padx=40, fill="both", expand=True)

        # Left Column: Formats
        self.left_frame = ctk.CTkFrame(self.settings_frame, fg_color="transparent")
        self.left_frame.pack(side="left", fill="both", expand=True, padx=15, pady=15)

        self.type_label = ctk.CTkLabel(self.left_frame, text="1. Target Output Type:", font=("Arial", 11, "bold"))
        self.type_label.pack(anchor="w", pady=2)
        self.type_menu = ctk.CTkOptionMenu(self.left_frame, values=["Video (.MP4/.MKV)", "Audio Only (.MP3/.M4A)", "Thumbnail Only (.JPG)"], command=self.toggle_type)
        self.type_menu.set(self.settings_mgr.get("last_type"))
        self.type_menu.pack(fill="x", pady=(0, 15))

        self.quality_label = ctk.CTkLabel(self.left_frame, text="2. Resolution / Quality Bitrate:", font=("Arial", 11, "bold"))
        self.quality_label.pack(anchor="w", pady=2)
        self.quality_menu = ctk.CTkOptionMenu(self.left_frame, values=["Best Available", "1080p (FHD)", "720p (HD)", "480p", "360p"])
        self.quality_menu.set(self.settings_mgr.get("last_quality"))
        self.quality_menu.pack(fill="x")

        # Right Column: Power User Switches
        self.right_frame = ctk.CTkFrame(self.settings_frame, fg_color="transparent")
        self.right_frame.pack(side="right", fill="both", expand=True, padx=15, pady=15)

        self.opts_label = ctk.CTkLabel(self.right_frame, text="3. Extra Modifiers:", font=("Arial", 11, "bold"))
        self.opts_label.pack(anchor="w", pady=2)

        self.playlist_switch = ctk.CTkSwitch(self.right_frame, text="Download Full Playlists")
        if self.settings_mgr.get("playlist_enabled"): self.playlist_switch.select()
        self.playlist_switch.pack(anchor="w", pady=6)

        self.sub_switch = ctk.CTkSwitch(self.right_frame, text="Embed English Subtitles")
        if self.settings_mgr.get("subtitles_enabled"): self.sub_switch.select()
        self.sub_switch.pack(anchor="w", pady=6)

        self.compat_switch = ctk.CTkSwitch(self.right_frame, text="No-FFmpeg Safe Fallback")
        if self.settings_mgr.get("no_ffmpeg_enabled"): self.compat_switch.select()
        self.compat_switch.pack(anchor="w", pady=6)
        self.compat_tip = ctk.CTkLabel(self.right_frame, text="*Enable if conversions fail or throw errors", font=("Arial", 10, "italic"), text_color="gray")
        self.compat_tip.pack(anchor="w", padx=5)

        # 4. Progress Statistics Tracking Panel
        self.stats_frame = ctk.CTkFrame(self, height=60, fg_color="transparent")
        self.stats_frame.pack(fill="x", padx=40, pady=5)
        
        self.speed_lbl = ctk.CTkLabel(self.stats_frame, text="Speed: --", font=("Arial", 11), text_color="gray")
        self.speed_lbl.pack(side="left", padx=10)
        
        self.eta_lbl = ctk.CTkLabel(self.stats_frame, text="ETA: --", font=("Arial", 11), text_color="gray")
        self.eta_lbl.pack(side="right", padx=10)

        # 5. Core Execution Action Controls
        self.download_btn = ctk.CTkButton(self, text="⚡ EXECUTE DOWNLOAD TASK", font=("Arial", 14, "bold"), height=50, fg_color="#2b8a3e", hover_color="#237032", command=self.trigger_download)
        self.download_btn.pack(pady=(5, 5), padx=40, fill="x")

        self.progress_bar = ctk.CTkProgressBar(self)
        self.progress_bar.pack(pady=10, padx=40, fill="x")
        self.progress_bar.set(0)

        self.status_label = ctk.CTkLabel(self, text="System Standby - Ready", text_color="#1c7ed6", font=("Arial", 12, "bold"))
        self.status_label.pack(pady=(0, 15))

        # 6. Footer (Version & Updates)
        self.footer_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.footer_frame.pack(side="bottom", fill="x", padx=20, pady=10)
        
        self.version_lbl = ctk.CTkLabel(self.footer_frame, text="v1.0.0", font=("Arial", 10), text_color="gray")
        self.version_lbl.pack(side="left")
        
        self.update_btn = ctk.CTkButton(self.footer_frame, text="Check for Updates", width=120, height=24, font=("Arial", 10), command=self.check_updates)
        self.update_btn.pack(side="right")

    def on_url_change(self, event=None):
        url = self.url_entry.get().strip()
        if url == self.current_metadata_url:
            return
            
        if not url.startswith(('http://', 'https://', 'www.')):
            self.preview_frame.pack_forget()
            return

        self.current_metadata_url = url
        # Debounce to avoid too many requests while typing
        if hasattr(self, '_metadata_job'):
            self.after_cancel(self._metadata_job)
        self._metadata_job = self.after(1000, lambda: threading.Thread(target=self.fetch_metadata, args=(url,), daemon=True).start())

    def fetch_metadata(self, url):
        try:
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'extract_flat': True,
                'skip_download': True,
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                
                title = info.get('title', 'Unknown Title')
                duration_sec = info.get('duration', 0)
                thumbnail_url = info.get('thumbnail')
                
                # Format duration
                minutes, seconds = divmod(duration_sec, 60)
                hours, minutes = divmod(minutes, 60)
                if hours > 0:
                    duration_str = f"Duration: {hours:02d}:{minutes:02d}:{seconds:02d}"
                else:
                    duration_str = f"Duration: {minutes:02d}:{seconds:02d}"
                
                # Load thumbnail
                ctk_image = None
                if thumbnail_url:
                    try:
                        response = requests.get(thumbnail_url, timeout=5)
                        response.raise_for_status()
                        img_data = Image.open(BytesIO(response.content))
                        # Maintain aspect ratio for the preview
                        img_data.thumbnail((120, 68))
                        ctk_image = ctk.CTkImage(light_image=img_data, dark_image=img_data, size=(120, 68))
                    except requests.exceptions.RequestException as re:
                        logger.error(f"Thumbnail network error: {re}")
                    except Exception as ie:
                        logger.error(f"Thumbnail processing error: {ie}")

                # Update UI in main thread
                self.after(0, lambda: self.update_preview(title, duration_str, ctk_image))
                
        except yt_dlp.utils.DownloadError as de:
            logger.error(f"Metadata extraction error: {de}")
            self.after(0, lambda: self.preview_frame.pack_forget())
        except Exception as e:
            logger.error(f"General metadata error: {e}")
            self.after(0, lambda: self.preview_frame.pack_forget())

    def update_preview(self, title, duration, image):
        self.video_title_lbl.configure(text=title)
        self.video_duration_lbl.configure(text=duration)
        if image:
            self.thumb_label.configure(image=image, text="")
        else:
            self.thumb_label.configure(image=None, text="No Preview")
        
        # Insert preview after URL section
        self.preview_frame.pack(pady=5, padx=40, fill="x", after=self.url_entry)

    def toggle_theme(self):
        if self.theme_switch.get() == 1:
            self.appearance_mode = "Dark"
        else:
            self.appearance_mode = "Light"
        ctk.set_appearance_mode(self.appearance_mode)
        self.save_current_settings()

    def choose_folder(self):
        folder = filedialog.askdirectory(initialdir=self.save_dir)
        if folder:
            self.save_dir = folder
            display_path = f"...{folder[-45:]}" if len(folder) > 45 else folder
            self.loc_label.configure(text=f"Save Folder: {display_path}")
            self.save_current_settings()

    def quick_open_folder(self):
        self.open_media(self.save_dir, is_folder=True)

    def toggle_type(self, choice):
        if "Audio Only" in choice:
            self.quality_menu.configure(values=["Best Audio Quality", "320kbps (HQ MP3)", "192kbps (MQ MP3)", "128kbps (M4A)"])
            self.quality_menu.set("Best Audio Quality")
            self.sub_switch.configure(state="disabled")
        elif "Thumbnail Only" in choice:
            self.quality_menu.configure(values=["Maximum Resolution Image"])
            self.quality_menu.set("Maximum Resolution Image")
            self.sub_switch.configure(state="disabled")
        else:
            self.quality_menu.configure(values=["Best Available", "1080p (FHD)", "720p (HD)", "480p", "360p"])
            self.quality_menu.set("Best Available")
            self.sub_switch.configure(state="normal")
        self.save_current_settings()

    def yt_dlp_hook(self, d):
        if d['status'] == 'downloading':
            try:
                total = d.get('total_bytes') or d.get('total_bytes_estimate') or 0
                downloaded = d.get('downloaded_bytes', 0)
                
                if total > 0:
                    percent = downloaded / total
                    self.progress_bar.set(percent)
                
                speed = d.get('_speed_str', 'Uncalculating')
                eta = d.get('_eta_str', '--:--')
                percent_str = d.get('_percent_str', '0.0%')
                
                self.speed_lbl.configure(text=f"Speed: {speed.strip()}")
                self.eta_lbl.configure(text=f"Time Left: {eta.strip()}")
                self.status_label.configure(text=f"Downloading Components... {percent_str.strip()}", text_color="#1c7ed6")
            except Exception as e:
                logger.debug(f"Hook error: {e}")
        elif d['status'] == 'finished':
            self.progress_bar.set(1.0)
            self.status_label.configure(text="Assembling streams & applying modifications...", text_color="orange")

    def trigger_download(self):
        # Dispatched to a separate runtime thread to block interface hanging
        threading.Thread(target=self.run_download, daemon=True).start()

    def run_download(self, retry_with_fallback=False):
        url = self.url_entry.get().strip()
        if not url:
            self.status_label.configure(text="Operation Cancelled: URL Entry box is empty!", text_color="#c92a2a")
            return

        self.download_btn.configure(state="disabled")
        
        if retry_with_fallback:
            self.status_label.configure(text="Primary method failed. Attempting Safe Fallback...", text_color="orange")
            logger.warning(f"Retrying download with fallback for URL: {url}")
        else:
            self.status_label.configure(text="Connecting to streaming servers...", text_color="orange")
            self.progress_bar.set(0.0)
            self.start_time = time.time()

        media_type = self.type_menu.get()
        quality = self.quality_menu.get()
        no_ffmpeg = self.compat_switch.get() or retry_with_fallback # Auto-enable fallback
        get_playlist = self.playlist_switch.get()
        get_subs = self.sub_switch.get() and not retry_with_fallback # Disable subs on fallback to reduce complexity

        ydl_opts = {
            'outtmpl': os.path.join(self.save_dir, '%(title)s.%(ext)s'),
            'progress_hooks': [self.yt_dlp_hook],
            'noplaylist': not get_playlist,
            'logger': logger,
            'ignoreerrors': True, # Don't crash on individual playlist item errors
        }

        # Subtitle Embedder Processing Engine
        if get_subs and "Video" in media_type:
            ydl_opts.update({
                'writesubtitles': True,
                'subtitleslangs': ['en'],
                'postprocessors': [{
                    'key': 'FFmpegEmbedSubtitle',
                    'already_have_subtitle': False,
                }]
            })

        # Thumbnail Extraction Configuration
        if "Thumbnail" in media_type:
            ydl_opts.update({
                'skip_download': True,
                'writethumbnail': True,
                'outtmpl': os.path.join(self.save_dir, '%(title)s.%(ext)s'),
            })
        
        # Audio/Video Standard & Compatibility Configuration Matrix
        elif no_ffmpeg:
            # SAFE FALLBACK MODE: Focus on compatibility over quality
            if "Audio" in media_type:
                ydl_opts['format'] = 'bestaudio/best'
            else:
                # Force standard MP4 compatibility
                ydl_opts['format'] = 'best[ext=mp4]/best'
        else:
            if "Audio" in media_type:
                codec = 'mp3' if 'MP3' in quality else 'm4a'
                bitrate = '320' if '320' in quality else ('192' if '192' in quality else '0')
                ydl_opts.update({
                    'format': 'bestaudio/best',
                    'postprocessors': [{
                        'key': 'FFmpegExtractAudio',
                        'preferredcodec': codec,
                        'preferredquality': bitrate,
                    }],
                })
            else:
                if "1080p" in quality: res_str = "bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best"
                elif "720p" in quality: res_str = "bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best"
                elif "480p" in quality: res_str = "bestvideo[height<=480][ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best"
                elif "360p" in quality: res_str = "bestvideo[height<=360][ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best"
                else: res_str = "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best"
                ydl_opts['format'] = res_str

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # Add validation for URL format before attempting download
                if not url.startswith(('http://', 'https://', 'www.')):
                    raise ValueError("Invalid URL format. Please provide a valid YouTube link.")

                info = ydl.extract_info(url, download=True)
                
                if info is None:
                    raise yt_dlp.utils.DownloadError("Failed to extract video information.")

                if 'entries' in info:
                    self.status_label.configure(text="Playlist Download Successful!", text_color="#2b8a3e")
                    self.open_media(self.save_dir, is_folder=True)
                else:
                    file_path = ydl.prepare_filename(info)
                    
                    if "Thumbnail" in media_type:
                        file_path = os.path.splitext(file_path)[0] + ".jpg"
                    elif "Audio" in media_type and not no_ffmpeg:
                        file_path = os.path.splitext(file_path)[0] + f".{codec}"
                    
                    if not os.path.exists(file_path):
                        # Some formats might have different extensions, attempt a fuzzy check
                        base_path = os.path.splitext(file_path)[0]
                        possible_files = [f for f in os.listdir(self.save_dir) if f.startswith(os.path.basename(base_path))]
                        if possible_files:
                            file_path = os.path.join(self.save_dir, possible_files[0])
                        else:
                            raise FileNotFoundError(f"Could not locate the downloaded file: {os.path.basename(file_path)}")
                        
                    self.status_label.configure(text="Finished! Launching Media Player...", text_color="#2b8a3e")
                    self.open_media(file_path)
                    
        except Exception as e:
            logger.error(f"Download attempt failed: {e}")
            
            if not retry_with_fallback:
                # First failure: Attempt fallback automatically
                logger.info("Initiating automatic fallback retry...")
                self.run_download(retry_with_fallback=True)
                return # Important: exit the current thread execution
            
            # Second failure (after fallback): Show final error
            if isinstance(e, yt_dlp.utils.DownloadError):
                self.status_label.configure(text="Download Failed! Check URL or availability.", text_color="#c92a2a")
                messagebox.showerror("Download Error", f"YouTube-DLP encountered an error even in safe mode:\n\n{str(e).split(';')[0]}")
            elif isinstance(e, ValueError):
                self.status_label.configure(text="Invalid Input!", text_color="#c92a2a")
                messagebox.showwarning("Input Error", str(e))
            else:
                logger.error(traceback.format_exc())
                self.status_label.configure(text="Execution Broken! Check logs.", text_color="#c92a2a")
                messagebox.showerror("Critical Error", f"An unexpected error occurred after fallback attempt:\n{str(e)}")
        finally:
            # Only reset button and labels if we aren't about to retry
            if not (not retry_with_fallback and 'e' in locals()):
                self.speed_lbl.configure(text="Speed: --")
                self.eta_lbl.configure(text="Time Left: --")
                self.download_btn.configure(state="normal")
                self.save_current_settings()

    def open_media(self, path, is_folder=False):
        try:
            current_os = platform.system()
            target = path if os.path.exists(path) and not is_folder else self.save_dir
            
            if current_os == "Windows":
                os.startfile(target)
            elif current_os == "Darwin":
                subprocess.call(["open", target])
            else:
                subprocess.call(["xdg-open", target])
        except Exception as e:
            logger.error(f"Error opening media: {e}")

    def check_updates(self):
        def run_check():
            try:
                self.update_btn.configure(state="disabled", text="Checking...")
                api_url = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
                response = requests.get(api_url, timeout=10)
                response.raise_for_status()
                data = response.json()
                
                latest_version = data.get("tag_name", VERSION)
                
                if latest_version != VERSION:
                    if messagebox.askyesno("Update Available", f"A new version ({latest_version}) is available!\n\nWould you like to visit the download page?"):
                        import webbrowser
                        webbrowser.open(data.get("html_url", f"https://github.com/{GITHUB_REPO}/releases"))
                else:
                    messagebox.showinfo("Update Check", f"You are running the latest version ({VERSION}).")
                    
            except Exception as e:
                logger.error(f"Update check failed: {e}")
                messagebox.showerror("Update Error", "Could not check for updates. Please check your internet connection.")
            finally:
                self.update_btn.configure(state="normal", text="Check for Updates")

        threading.Thread(target=run_check, daemon=True).start()

    def save_current_settings(self):
        settings = {
            "appearance_mode": self.appearance_mode,
            "save_dir": self.save_dir,
            "window_geometry": self.geometry(),
            "last_quality": self.quality_menu.get(),
            "last_type": self.type_menu.get(),
            "playlist_enabled": self.playlist_switch.get() == 1,
            "subtitles_enabled": self.sub_switch.get() == 1,
            "no_ffmpeg_enabled": self.compat_switch.get() == 1
        }
        self.settings_mgr.save_settings(settings)

    def on_closing(self):
        self.save_current_settings()
        self.destroy()

if __name__ == "__main__":
    try:
        app = MegaDownloader()
        app.protocol("WM_DELETE_WINDOW", app.on_closing)
        app.mainloop()
    except Exception as e:
        logger.critical(f"Unhandled exception: {e}")
        logger.critical(traceback.format_exc())