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
import tempfile
import hashlib
import sys
# import webbrowser  # unused
from PIL import Image
from io import BytesIO
from pathlib import Path
from tkinter import filedialog, messagebox

# Local imports
from logger_config import setup_logging
from dependency_manager import check_dependencies
from settings_manager import SettingsManager
from utils import sanitize_filename

# Initialize logging
logger = setup_logging()

# Constants
GITHUB_REPO = "Abel-Ajish/YT-Downloader"
VERSION = "v1.1.0"

class MegaDownloader(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Load Settings
        self.settings_mgr = SettingsManager()
        
        # Window Setup
        self.title("Youtube Audio/Video Downloader")
        
        # Calculate Half Screen Size
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        half_width = screen_width // 2
        
        # Load Settings or Default to Half Screen
        geometry = self.settings_mgr.get("window_geometry", f"{half_width}x{screen_height}+0+0")
        self.geometry(geometry)
        self.minsize(700, 750)
        self.resizable(True, True)

        # Force Fullscreen on first launch if not already set
        if not self.settings_mgr.get("has_launched_before", False):
            self.after(100, lambda: self.state('zoomed'))
            self.settings_mgr.save_settings({"has_launched_before": True})
        
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
        # --- Main Container (Non-Scrollable for Full Screen Density) ---
        self.main_container = ctk.CTkFrame(self, fg_color="transparent")
        self.main_container.pack(fill="both", expand=True, padx=5, pady=5)

        # Header & Theme Toggle
        self.header_frame = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.header_frame.pack(pady=(10, 2), fill="x", padx=40)
        
        self.title_lbl = ctk.CTkLabel(self.header_frame, text="Youtube Audio/Video Downloader", font=("Arial", 18, "bold"))
        self.title_lbl.pack(side="left")
        
        self.theme_switch = ctk.CTkSwitch(self.header_frame, text="Dark Mode", command=self.toggle_theme)
        if self.appearance_mode == "Dark":
            self.theme_switch.select()
        else:
            self.theme_switch.deselect()
        self.theme_switch.pack(side="right")

        # --- Top Info Bar ---
        self.top_info_frame = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.top_info_frame.pack(pady=(0, 5), fill="x", padx=40)
        
        self.version_lbl = ctk.CTkLabel(self.top_info_frame, text=VERSION, font=("Arial", 10), text_color="gray")
        self.version_lbl.pack(side="left")
        
        self.update_btn = ctk.CTkButton(self.top_info_frame, text="Check for Updates", width=120, height=24, font=("Arial", 10, "bold"), command=self.check_updates)
        self.update_btn.pack(side="right")

        # 1. URL Input Section
        self.url_label = ctk.CTkLabel(self.main_container, text="YouTube URL Link:", font=("Arial", 11, "bold"))
        self.url_label.pack(anchor="w", padx=40, pady=(5, 0))
        
        self.url_entry = ctk.CTkEntry(self.main_container, placeholder_text="https://www.youtube.com/watch?v=...", height=28)
        self.url_entry.pack(pady=2, padx=40, fill="x")
        self.url_entry.bind("<KeyRelease>", self.on_url_change)
        self.url_entry.bind("<<Paste>>", lambda e: self.after(10, self.on_url_change))

        # 1.5 Metadata Preview Section
        self.preview_frame = ctk.CTkFrame(self.main_container, fg_color="transparent", height=60)
        self.preview_frame.pack(pady=2, padx=40, fill="x")
        self.preview_frame.pack_forget() 

        self.thumb_label = ctk.CTkLabel(self.preview_frame, text="", width=100, height=56)
        self.thumb_label.pack(side="left", padx=(0, 10))

        self.info_frame = ctk.CTkFrame(self.preview_frame, fg_color="transparent")
        self.info_frame.pack(side="left", fill="both", expand=True)

        self.video_title_lbl = ctk.CTkLabel(self.info_frame, text="Video Title", font=("Arial", 11, "bold"), anchor="w", wraplength=500)
        self.video_title_lbl.pack(fill="x")

        self.video_duration_lbl = ctk.CTkLabel(self.info_frame, text="Duration: 00:00", font=("Arial", 10), text_color="gray", anchor="w")
        self.video_duration_lbl.pack(fill="x")

        # 2. Storage Directory Configuration
        self.loc_frame = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.loc_frame.pack(pady=5, fill="x", padx=40)
        
        display_path = self.save_dir
        if len(display_path) > 50:
            display_path = f"...{display_path[-50:]}"
            
        self.loc_label = ctk.CTkLabel(self.loc_frame, text=f"Save Folder: {display_path}", text_color="gray", font=("Arial", 10))
        self.loc_label.pack(side="left", fill="x", expand=True, anchor="w")
        
        self.open_folder_btn = ctk.CTkButton(self.loc_frame, text="📂 Folder", width=90, height=28, fg_color="#495057", hover_color="#343a40", command=self.quick_open_folder)
        self.open_folder_btn.pack(side="right", padx=(0, 10))
        
        self.loc_btn = ctk.CTkButton(self.loc_frame, text="Change", width=90, height=28, command=self.choose_folder)
        self.loc_btn.pack(side="right")

        # 3. Features & Settings Dashboard
        self.settings_frame = ctk.CTkFrame(self.main_container)
        self.settings_frame.pack(pady=5, padx=40, fill="x")

        self.left_frame = ctk.CTkFrame(self.settings_frame, fg_color="transparent")
        self.left_frame.pack(side="left", fill="both", expand=True, padx=10, pady=10)

        self.type_label = ctk.CTkLabel(self.left_frame, text="Output Type:", font=("Arial", 10, "bold"))
        self.type_label.pack(anchor="w")
        self.type_menu = ctk.CTkOptionMenu(self.left_frame, values=["Video (.MP4/.MKV)", "Audio Only (.MP3/.M4A)", "Thumbnail Only (.JPG)"], command=self.toggle_type, height=26)
        self.type_menu.set(self.settings_mgr.get("last_type"))
        self.type_menu.pack(fill="x", pady=(0, 10))

        self.quality_label = ctk.CTkLabel(self.left_frame, text="Quality:", font=("Arial", 10, "bold"))
        self.quality_label.pack(anchor="w")
        self.quality_menu = ctk.CTkOptionMenu(self.left_frame, values=["Best Available", "1080p (FHD)", "720p (HD)", "480p", "360p"], height=26)
        self.quality_menu.set(self.settings_mgr.get("last_quality"))
        self.quality_menu.pack(fill="x")

        self.right_frame = ctk.CTkFrame(self.settings_frame, fg_color="transparent")
        self.right_frame.pack(side="right", fill="both", expand=True, padx=10, pady=10)

        self.post_action_label = ctk.CTkLabel(self.right_frame, text="After Download:", font=("Arial", 10, "bold"))
        self.post_action_label.pack(anchor="w")
        self.post_action_menu = ctk.CTkOptionMenu(self.right_frame, values=["Do Nothing", "Open File", "Open Folder", "Shutdown PC"], height=26)
        self.post_action_menu.set(self.settings_mgr.get("post_action", "Do Nothing"))
        self.post_action_menu.pack(fill="x")

        # 3.5 Advanced Settings Section (Collapsible)
        self.adv_header = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.adv_header.pack(pady=5, padx=40, fill="x")
        
        self.adv_toggle_btn = ctk.CTkButton(self.adv_header, text="▶ Show Advanced Settings", width=200, height=24, font=("Arial", 10, "bold"), fg_color=("gray85", "gray25"), text_color=("black", "white"), hover_color=("gray75", "gray35"), border_width=1, command=self.toggle_advanced)
        self.adv_toggle_btn.pack(anchor="center")

        self.adv_frame = ctk.CTkFrame(self.main_container)
        # self.adv_frame is NOT packed by default
        
        self.adv_content = ctk.CTkFrame(self.adv_frame, fg_color="transparent")
        self.adv_content.pack(fill="x", padx=10, pady=10)

        self.adv_left = ctk.CTkFrame(self.adv_content, fg_color="transparent")
        self.adv_left.pack(side="left", fill="both", expand=True)

        self.codec_label = ctk.CTkLabel(self.adv_left, text="Codec:", font=("Arial", 9, "bold"))
        self.codec_label.pack(anchor="w")
        self.codec_menu = ctk.CTkOptionMenu(self.adv_left, values=["H.264 (Most Compatible)", "H.265 (High Efficiency)", "VP9 (Best for YouTube)"], height=24, font=("Arial", 10))
        self.codec_menu.set(self.settings_mgr.get("preferred_codec", "H.264 (Most Compatible)"))
        self.codec_menu.pack(fill="x")

        # Update channel selector (stable | beta)
        self.update_channel_label = ctk.CTkLabel(self.adv_left, text="Update Channel:", font=("Arial", 9, "bold"))
        self.update_channel_label.pack(anchor="w", pady=(8, 0))
        self.update_channel_menu = ctk.CTkOptionMenu(self.adv_left, values=["stable", "beta"], height=22)
        self.update_channel_menu.set(self.settings_mgr.get("update_channel", "stable"))
        self.update_channel_menu.pack(fill="x", pady=(0, 6))

        self.adv_right = ctk.CTkFrame(self.adv_content, fg_color="transparent")
        self.adv_right.pack(side="right", fill="both", expand=True, padx=(10, 0))

        self.playlist_switch = ctk.CTkSwitch(self.adv_right, text="Playlist", font=("Arial", 9))
        if self.settings_mgr.get("playlist_enabled"): self.playlist_switch.select()
        self.playlist_switch.pack(anchor="w")

        self.sub_switch = ctk.CTkSwitch(self.adv_right, text="Subtitles", font=("Arial", 9))
        if self.settings_mgr.get("subtitles_enabled"): self.sub_switch.select()
        self.sub_switch.pack(anchor="w")

        self.compat_switch = ctk.CTkSwitch(self.adv_right, text="Safe Mode", font=("Arial", 9))
        if self.settings_mgr.get("no_ffmpeg_enabled"): self.compat_switch.select()
        self.compat_switch.pack(anchor="w")

        # Telemetry opt-in (disabled by default per user policy)
        self.telemetry_switch = ctk.CTkSwitch(self.adv_right, text="Telemetry Opt-in", font=("Arial", 9))
        if self.settings_mgr.get("telemetry_opt_in"):
            self.telemetry_switch.select()
        else:
            self.telemetry_switch.deselect()
        self.telemetry_switch.pack(anchor="w", pady=(6, 0))

        # 4. Progress Statistics Tracking Panel
        self.stats_frame = ctk.CTkFrame(self.main_container, height=40, fg_color="transparent")
        self.stats_frame.pack(fill="x", padx=40, pady=2)
        
        self.speed_lbl = ctk.CTkLabel(self.stats_frame, text="Speed: --", font=("Arial", 10), text_color="gray")
        self.speed_lbl.pack(side="left", padx=10)
        
        self.eta_lbl = ctk.CTkLabel(self.stats_frame, text="ETA: --", font=("Arial", 10), text_color="gray")
        self.eta_lbl.pack(side="right", padx=10)

        # 5. Core Execution Action Controls
        self.download_btn = ctk.CTkButton(self.main_container, text="⚡ EXECUTE DOWNLOAD TASK", font=("Arial", 14, "bold"), height=45, fg_color="#2b8a3e", hover_color="#237032", command=self.trigger_download)
        self.download_btn.pack(pady=2, padx=40, fill="x")

        self.progress_bar = ctk.CTkProgressBar(self.main_container, height=12)
        self.progress_bar.pack(pady=5, padx=40, fill="x")
        self.progress_bar.set(0)

        self.status_label = ctk.CTkLabel(self.main_container, text="System Standby - Ready", text_color="#1c7ed6", font=("Arial", 11, "bold"))
        self.status_label.pack(pady=2)

        # 5.5 Download History Button
        self.history_btn = ctk.CTkButton(self.main_container, text="📜 View Download History", height=28, fg_color=("gray85", "gray25"), text_color=("black", "white"), hover_color=("gray75", "gray35"), border_width=1, command=self.show_history, font=("Arial", 10))
        self.history_btn.pack(pady=(0, 10))

    def on_url_change(self, event=None):
        url = self.url_entry.get().strip()
        if url == self.current_metadata_url:
            return
            
        if not url.startswith(('http://', 'https://', 'www.')):
            self.preview_frame.pack_forget()
            return

        # Show a "Loading" state immediately if it looks like a full link
        if len(url) > 15: 
            self.video_title_lbl.configure(text="Fetching video details...")
            self.video_duration_lbl.configure(text="Please wait...")
            self.thumb_label.configure(image=None, text="⌛")
            self.preview_frame.pack(pady=2, padx=40, fill="x", after=self.url_entry)

        self.current_metadata_url = url
        # Debounce to avoid too many requests while typing - reduced to 300ms for "immediate" feel
        if hasattr(self, '_metadata_job'):
            self.after_cancel(self._metadata_job)
        self._metadata_job = self.after(300, lambda: threading.Thread(target=self.fetch_metadata, args=(url,), daemon=True).start())

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
                
                # Load thumbnail as PIL Image (Thread-safe)
                pil_image = None
                if thumbnail_url:
                    try:
                        response = requests.get(thumbnail_url, timeout=5)
                        response.raise_for_status()
                        pil_image = Image.open(BytesIO(response.content))
                        # Pre-resize to maintain aspect ratio
                        pil_image.thumbnail((120, 68))
                    except requests.exceptions.RequestException as re:
                        logger.error(f"Thumbnail network error: {re}")
                    except Exception as ie:
                        logger.error(f"Thumbnail processing error: {ie}")

                # Update UI in main thread - Pass the PIL image, not CTkImage
                self.after(0, lambda: self.update_preview(title, duration_str, pil_image))
                
        except yt_dlp.utils.DownloadError as de:
            logger.error(f"Metadata extraction error: {de}")
            self.after(0, lambda: self.preview_frame.pack_forget())
        except Exception as e:
            logger.error(f"General metadata error: {e}")
            self.after(0, lambda: self.preview_frame.pack_forget())

    def update_preview(self, title, duration, pil_image):
        self.video_title_lbl.configure(text=title)
        self.video_duration_lbl.configure(text=duration)
        
        if pil_image:
            # Create CTkImage in the main thread to avoid TclError
            ctk_image = ctk.CTkImage(light_image=pil_image, dark_image=pil_image, size=(120, 68))
            self.thumb_label.configure(image=ctk_image, text="")
            # Keep a reference to prevent garbage collection
            self.thumbnail_image = ctk_image
        else:
            self.thumb_label.configure(image=None, text="No Preview")
        
        # Insert preview after URL section
        self.preview_frame.pack(pady=5, padx=40, fill="x", after=self.url_entry)

    def show_history(self):
        history_window = ctk.CTkToplevel(self)
        history_window.title("Download History")
        history_window.geometry("500x450")
        history_window.attributes("-topmost", True)

        history = self.settings_mgr.get("download_history", [])
        
        label = ctk.CTkLabel(history_window, text="Recent Downloads", font=("Arial", 16, "bold"))
        label.pack(pady=10)

        scroll_frame = ctk.CTkScrollableFrame(history_window, width=450, height=300)
        scroll_frame.pack(padx=20, pady=10, fill="both", expand=True)

        if not history:
            ctk.CTkLabel(scroll_frame, text="No history yet.").pack(pady=20)
        else:
            for item in reversed(history):
                item_frame = ctk.CTkFrame(scroll_frame)
                item_frame.pack(fill="x", pady=5, padx=5)
                
                title = item.get("title", "Unknown")
                date = item.get("date", "")
                
                ctk.CTkLabel(item_frame, text=title, font=("Arial", 11, "bold"), anchor="w").pack(side="left", padx=10, fill="x", expand=True)
                ctk.CTkLabel(item_frame, text=date, font=("Arial", 10), text_color="gray").pack(side="right", padx=10)

        def clear_and_refresh():
            if messagebox.askyesno("Clear History", "Are you sure you want to delete all download history?", parent=history_window):
                self.settings_mgr.save_settings({"download_history": []})
                history_window.destroy()
                self.show_history()

        clear_btn = ctk.CTkButton(history_window, text="🗑️ Clear Download History", fg_color="#c92a2a", hover_color="#a52828", 
                                 height=32, font=("Arial", 12, "bold"), command=clear_and_refresh)
        clear_btn.pack(pady=15)

    def clear_history_direct(self):
        if messagebox.askyesno("Clear History", "Are you sure you want to delete all download history?"):
            self.settings_mgr.save_settings({"download_history": []})
            messagebox.showinfo("Success", "Download history has been cleared.")

    def save_to_history(self, title):
        history = self.settings_mgr.get("download_history", [])
        history.append({
            "title": title,
            "date": time.strftime("%Y-%m-%d %H:%M"),
            "url": self.url_entry.get()
        })
        # Keep only last 50 items
        if len(history) > 50:
            history = history[-50:]
        self.settings_mgr.save_settings({"download_history": history})

    def toggle_advanced(self):
        if self.adv_frame.winfo_viewable():
            self.adv_frame.pack_forget()
            self.adv_toggle_btn.configure(text="▶ Show Advanced Settings")
        else:
            # Insert after the header button
            self.adv_frame.pack(pady=5, padx=40, fill="x", after=self.adv_header)
            self.adv_toggle_btn.configure(text="▼ Hide Advanced Settings")

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

                speed = d.get('_speed_str', 'Uncalculating')
                eta = d.get('_eta_str', '--:--')
                percent_str = d.get('_percent_str', '0.0%')

                def _update_progress():
                    try:
                        if total > 0:
                            percent = downloaded / total
                            self.progress_bar.set(percent)
                        self.speed_lbl.configure(text=f"Speed: {speed.strip()}")
                        self.eta_lbl.configure(text=f"Time Left: {eta.strip()}")
                        self.status_label.configure(text=f"Downloading Components... {percent_str.strip()}", text_color="#1c7ed6")
                    except Exception:
                        logger.debug("UI update failed in progress hook")

                self.after(0, _update_progress)
            except Exception as e:
                logger.debug(f"Hook error: {e}")
        elif d['status'] == 'finished':
            def _update_finished():
                try:
                    self.progress_bar.set(1.0)
                    self.status_label.configure(text="Assembling streams & applying modifications...", text_color="orange")
                except Exception:
                    logger.debug("UI update failed on finished hook")

            self.after(0, _update_finished)

    def trigger_download(self):
        # Dispatched to a separate runtime thread to block interface hanging
        threading.Thread(target=self.run_download, daemon=True).start()

    def run_download(self, retry_with_fallback=False, attempt=1):
        url = self.url_entry.get().strip()
        if not url:
            self.after(0, lambda: self.status_label.configure(text="Operation Cancelled: URL Entry box is empty!", text_color="#c92a2a"))
            return

        self.after(0, lambda: self.download_btn.configure(state="disabled"))
        retry_scheduled = False
        
        retry_limit = self.settings_mgr.get('download_retry_count', 2)
        if retry_with_fallback:
            # Use main-thread-safe update
            self.after(0, lambda: self.status_label.configure(text="Primary method failed. Attempting Safe Fallback...", text_color="orange"))
            logger.warning(f"Retrying download with fallback for URL: {url} (attempt {attempt})")
        else:
            self.after(0, lambda: self.status_label.configure(text="Connecting to streaming servers...", text_color="orange"))
            self.after(0, lambda: self.progress_bar.set(0.0))
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
            if not no_ffmpeg:
                ydl_opts['postprocessors'] = [{
                    'key': 'FFmpegThumbnailsConvertor',
                    'format': 'jpg',
                    'when': 'before_dl'
                }]
        
        # Audio/Video Standard & Compatibility Configuration Matrix
        elif no_ffmpeg:
            # SAFE FALLBACK MODE: Focus on compatibility over quality
            if "Audio" in media_type:
                # Force M4A for widest compatibility without FFmpeg
                ydl_opts['format'] = 'bestaudio[ext=m4a]/bestaudio/best'
            else:
                # Force standard MP4 compatibility
                ydl_opts['format'] = 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best'
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
                codec_choice = self.codec_menu.get()
                if "H.264" in codec_choice:
                    vcodec = "h264"
                elif "H.265" in codec_choice:
                    vcodec = "h265"
                else:
                    vcodec = "vp9"

                if "1080p" in quality: res_str = f"bestvideo[height<=1080][vcodec^={vcodec}][ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best"
                elif "720p" in quality: res_str = f"bestvideo[height<=720][vcodec^={vcodec}][ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best"
                elif "480p" in quality: res_str = f"bestvideo[height<=480][vcodec^={vcodec}][ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best"
                elif "360p" in quality: res_str = f"bestvideo[height<=360][vcodec^={vcodec}][ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best"
                else: res_str = f"bestvideo[vcodec^={vcodec}][ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best"
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
                    self.after(0, lambda: self.status_label.configure(text="Playlist Download Successful!", text_color="#2b8a3e"))
                    self.save_to_history(info.get('title', f"Playlist: {url[:20]}..."))
                    self.perform_post_action(self.save_dir)
                else:
                    original_title = info.get('title', 'Unknown')

                    # Prefer the actual output filename used by yt-dlp (available after download=True)
                    file_path = info.get('_filename') or ydl.prepare_filename(info)
                    # Sanitize title for history/UI only
                    safe_title = sanitize_filename(original_title)
                    info['title'] = safe_title
                    
                    if "Thumbnail" in media_type:
                        # Find the actual thumbnail file as it could be .webp, .jpg, .png
                        base_name = os.path.splitext(file_path)[0]
                        possible_extensions = ['.jpg', '.webp', '.png', '.jpeg']
                        found = False
                        for ext in possible_extensions:
                            if os.path.exists(base_name + ext):
                                file_path = base_name + ext
                                found = True
                                break
                        if not found:
                            # Try fuzzy search in the directory
                            possible_files = [f for f in os.listdir(self.save_dir) if f.startswith(os.path.basename(base_name))]
                            if possible_files:
                                file_path = os.path.join(self.save_dir, possible_files[0])

                    elif "Audio" in media_type:
                        if not no_ffmpeg:
                            file_path = os.path.splitext(file_path)[0] + f".{codec}"
                        else:
                            # Without ffmpeg, the extension is whatever was downloaded
                            if not os.path.exists(file_path):
                                base_name = os.path.splitext(file_path)[0]
                                possible_files = [f for f in os.listdir(self.save_dir) if f.startswith(os.path.basename(base_name))]
                                if possible_files:
                                    file_path = os.path.join(self.save_dir, possible_files[0])
                    
                    if not os.path.exists(file_path):
                        # Final fuzzy fallback
                        base_path = os.path.splitext(file_path)[0]
                        possible_files = [f for f in os.listdir(self.save_dir) if f.startswith(os.path.basename(base_path))]
                        if possible_files:
                            file_path = os.path.join(self.save_dir, possible_files[0])
                        else:
                            raise FileNotFoundError(f"Could not locate the downloaded file: {os.path.basename(file_path)}")
                    # Verify file integrity (basic check: non-zero size)
                    try:
                        size = os.path.getsize(file_path)
                        if size == 0:
                            raise IOError("Downloaded file has zero size")
                    except Exception as fexc:
                        logger.warning(f"Download verification failed for {file_path}: {fexc}")
                        raise

                    # Success
                    self.after(0, lambda: self.status_label.configure(text="Finished! Task Complete.", text_color="#2b8a3e"))
                    # Use the original (unsanitized) title in history for readability
                    self.save_to_history(original_title)
                    self.perform_post_action(file_path)
                    
        except Exception as e:
            logger.error(f"Download attempt failed: {e}")

            # If we haven't exhausted attempts, retry. Apply fallback on next attempt if not already using it.
            if attempt < retry_limit:
                logger.info(f"Retrying download (attempt {attempt + 1}/{retry_limit})...")
                # Schedule next attempt in a short delay to avoid tight loops
                next_fallback = retry_with_fallback or (attempt + 1 > 1)
                retry_scheduled = True
                self.after(500, lambda: threading.Thread(target=self.run_download, kwargs={'retry_with_fallback': next_fallback, 'attempt': attempt + 1}, daemon=True).start())
                return

            # Exhausted retries: present final failure to user
            if isinstance(e, yt_dlp.utils.DownloadError):
                self.after(0, lambda: self.status_label.configure(text="Download Failed! Check URL or availability.", text_color="#c92a2a"))
                self.after(0, lambda: messagebox.showerror("Download Error", f"YouTube-DLP encountered an error after {retry_limit} attempts:\n\n{str(e).split(';')[0]}"))
            elif isinstance(e, ValueError):
                self.after(0, lambda: self.status_label.configure(text="Invalid Input!", text_color="#c92a2a"))
                self.after(0, lambda: messagebox.showwarning("Input Error", str(e)))
            else:
                logger.error(traceback.format_exc())
                self.after(0, lambda: self.status_label.configure(text="Execution Broken! Check logs.", text_color="#c92a2a"))
                self.after(0, lambda: messagebox.showerror("Critical Error", f"An unexpected error occurred after {retry_limit} attempts:\n{str(e)}"))
        finally:
            if not retry_scheduled:
                self.after(0, lambda: self.speed_lbl.configure(text="Speed: --"))
                self.after(0, lambda: self.eta_lbl.configure(text="Time Left: --"))
                self.after(0, lambda: self.download_btn.configure(state="normal"))
                self.save_current_settings()

    def open_media(self, path, is_folder=False):
        try:
            current_os = platform.system()
            # Resolve to absolute path
            target = os.path.abspath(path)
            
            if not os.path.exists(target):
                logger.error(f"Target path does not exist: {target}")
                return

            if current_os == "Windows":
                os.startfile(target)
            elif current_os == "Darwin":
                subprocess.call(["open", target])
            else:
                subprocess.call(["xdg-open", target])
            logger.info(f"Opened {'folder' if is_folder else 'file'}: {target}")
        except Exception as e:
            logger.error(f"Error opening media: {e}")
            messagebox.showerror("Error", f"Could not open the {'folder' if is_folder else 'file'}.\n{str(e)}")

    def perform_post_action(self, file_path):
        action = self.post_action_menu.get()
        if action == "Open File":
            self.open_media(file_path)
        elif action == "Open Folder":
            target = file_path if os.path.isdir(file_path) else os.path.dirname(file_path)
            self.open_media(target, is_folder=True)
        elif action == "Shutdown PC":
            current_os = platform.system()
            if current_os == "Windows":
                os.system("shutdown /s /t 60")
                messagebox.showinfo("Shutdown", "PC will shutdown in 60 seconds. Save your work!")
            else:
                logger.warning("Shutdown not supported on this OS via this app.")

    def _run_in_main_thread(self, fn, *args, **kwargs):
        """Run a blocking function (like messagebox.askyesno) on the main thread and return its result."""
        ev = threading.Event()
        result = {'value': None}

        def _call():
            try:
                result['value'] = fn(*args, **kwargs)
            finally:
                ev.set()

        # Schedule on main thread
        self.after(0, _call)
        ev.wait()
        return result['value']

    def check_updates(self):
        def run_check():
            try:
                self.after(0, lambda: self.update_btn.configure(state="disabled", text="Checking..."))

                api_url = f"https://api.github.com/repos/{GITHUB_REPO}/releases"
                # Simple retry loop for transient network errors
                releases = None
                attempts = 0
                while attempts < 3:
                    try:
                        response = requests.get(api_url, timeout=12)
                        response.raise_for_status()
                        releases = response.json()
                        break
                    except requests.exceptions.RequestException as re:
                        attempts += 1
                        logger.warning(f"Update check network attempt {attempts} failed: {re}")
                        time.sleep(1 + attempts)
                if releases is None:
                    logger.error("Update check failed after retries")
                    self._run_in_main_thread(messagebox.showerror, "Update Error", "Could not check for updates. Please check your internet connection and try again.")
                    return

                channel = self.settings_mgr.get("update_channel", "stable")
                chosen = None
                if channel == "stable":
                    for r in releases:
                        if not r.get('prerelease'):
                            chosen = r
                            break
                else:
                    for r in releases:
                        if r.get('prerelease'):
                            chosen = r
                            break

                if not chosen:
                    # Handle the case where user has no stable releases yet but does have prereleases
                    if channel == 'stable':
                        prereleases = [r for r in releases if r.get('prerelease')]
                        if prereleases:
                            use_pr = self._run_in_main_thread(messagebox.askyesno, "No Stable Release Found", "No stable releases were found for this repository — your releases page currently contains only prereleases.\n\nWould you like to inspect/install the latest prerelease instead?")
                            if use_pr:
                                chosen = prereleases[0]
                            else:
                                return
                        else:
                            self._run_in_main_thread(messagebox.showinfo, "Update Check", f"No release found for channel: {channel}")
                            return
                    else:
                        self._run_in_main_thread(messagebox.showinfo, "Update Check", f"No release found for channel: {channel}")
                        return

                latest_version = chosen.get('tag_name', VERSION)
                if latest_version == VERSION:
                    self._run_in_main_thread(messagebox.showinfo, "Update Check", f"You are running the latest version ({VERSION}) for channel '{channel}'.")
                    return

                # Find an .exe asset to download (prefer Setup- or YT-Downloader)
                asset = None
                for a in chosen.get('assets', []):
                    name = a.get('name', '').lower()
                    if name.endswith('.exe') and ('setup' in name or 'yt-downloader' in name or 'yt_downloader' in name):
                        asset = a
                        break
                if not asset:
                    # fallback: first .exe
                    for a in chosen.get('assets', []):
                        if a.get('name', '').lower().endswith('.exe'):
                            asset = a
                            break

                if not asset:
                    self._run_in_main_thread(messagebox.showerror, "Update Error", "No installer asset (.exe) found in the selected release.")
                    return

                download_url = asset.get('browser_download_url')

                # GitHub release assets do not provide built-in digest fields; try to locate a checksum asset.
                expected_hash = None
                checksum_asset = next(
                    (a for a in chosen.get('assets', [])
                     if a.get('name', '') == f"{asset.get('name', '')}.sha256"),
                    None,
                )
                if checksum_asset and checksum_asset.get('browser_download_url'):
                    try:
                        txt = requests.get(checksum_asset['browser_download_url'], timeout=10).text
                        expected_hash = txt.strip().split()[0]
                    except Exception as exc:
                        logger.warning(f"Failed to fetch checksum asset: {exc}")
                # Ask user for consent to download and install
                proceed = self._run_in_main_thread(messagebox.askyesno, "Update Available", f"Version {latest_version} is available on channel '{channel}'.\n\nDo you want to download and install it now?")
                if not proceed:
                    return

                # Download to temp file (same dir as target exe for atomic replace)
                current_exe = Path(sys.executable) if getattr(sys, 'frozen', False) else None
                tmp_dir = os.path.dirname(str(current_exe)) if current_exe else None
                tmp = tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(asset.get('name', 'installer.exe'))[1], dir=tmp_dir)
                tmp_path = tmp.name
                try:
                    with requests.get(download_url, stream=True, timeout=30) as r:
                        r.raise_for_status()
                        for chunk in r.iter_content(chunk_size=8192):
                            if chunk:
                                tmp.write(chunk)
                    tmp.close()

                    # Verify checksum if available
                    if expected_hash:
                        h = hashlib.sha256()
                        with open(tmp_path, 'rb') as f:
                            for cb in iter(lambda: f.read(65536), b''):
                                h.update(cb)
                        if h.hexdigest().lower() != expected_hash.lower():
                            os.remove(tmp_path)
                            self._run_in_main_thread(messagebox.showerror, "Update Error", "Checksum mismatch for downloaded installer. Aborting.")
                            return
                    else:
                        # Warn user when no checksum is available
                        warn = self._run_in_main_thread(messagebox.askyesno, "No Checksum", "No checksum available for this asset. Proceed with installation? (Not recommended)")
                        if not warn:
                            try:
                                os.remove(tmp_path)
                            except Exception:
                                pass
                            return

                    # Decide how to run the downloaded exe:
                    # - If it's a Setup installer, launch it (installer will handle replacement/elevation)
                    # - If it's a standalone YT-Downloader.exe and we're running a frozen executable,
                    #   try to launch updater.py to perform atomic replacement of the running exe.
                    asset_name = asset.get('name', '').lower()

                    def _try_launch_updater(new_path, target_exe_path):
                        """Try to invoke updater.py to atomically replace target_exe_path with new_path.
                        Returns True if the updater process was started, False otherwise."""
                        updater_script = Path(__file__).resolve().parent / 'updater.py'
                        if not updater_script.exists():
                            return False

                        # Try a few common Python launchers. On Windows 'py' is usually available.
                        candidates = []
                        if sys.platform.startswith('win'):
                            candidates = ['py', 'python']
                        else:
                            # Prefer the current interpreter if it's a real Python (not a bundled exe)
                            if not getattr(sys, 'frozen', False):
                                candidates = [sys.executable]
                            candidates += ['python3', 'python']

                        for launcher in candidates:
                            try:
                                subprocess.Popen([launcher, str(updater_script), '--new', str(new_path), '--target', str(target_exe_path), '--wait-pid', str(os.getpid()), '--launch'], close_fds=True)
                                return True
                            except Exception:
                                continue
                        return False

                    launched = False
                    try:
                        if 'setup' in asset_name or 'setup-yt' in asset_name:
                            # Installer: launch it normally
                            if sys.platform.startswith('win'):
                                os.startfile(tmp_path)
                            elif sys.platform == 'darwin':
                                subprocess.Popen(['open', tmp_path])
                            else:
                                subprocess.Popen([tmp_path])
                            launched = True
                        else:
                            # Standalone exe. If running as a frozen exe, attempt atomic replacement via updater.
                            if current_exe and current_exe.exists():
                                # Attempt to run updater.py to replace the running exe
                                ok = _try_launch_updater(tmp_path, current_exe)
                                if ok:
                                    self._run_in_main_thread(messagebox.showinfo, "Updater Started", "Updater started to replace the application. The app will now exit to allow the update.")
                                    # Let the updater wait for our PID to exit, then we exit
                                    self.after(200, lambda: self.quit())
                                    launched = True
                                else:
                                    # Fallback: show error dialog telling user to run manually
                                    self._run_in_main_thread(messagebox.showerror, "Update Error", "Could not start the updater. Please run the downloaded installer manually.\n\nFile saved at: " + tmp_path)
                            else:
                                # Not running a frozen exe (e.g., running from source). Launch the downloaded exe as best-effort.
                                if sys.platform.startswith('win'):
                                    os.startfile(tmp_path)
                                else:
                                    subprocess.Popen([tmp_path])
                                launched = True
                    except Exception as exc:
                        logger.exception(f"Failed to launch installer/updater: {exc}")
                        # As a last resort, try to launch the file directly
                        try:
                            if sys.platform.startswith('win'):
                                os.startfile(tmp_path)
                            else:
                                subprocess.Popen([tmp_path])
                            launched = True
                        except Exception:
                            launched = False

                    if launched:
                        # Inform and exit so installer can update application files
                        self._run_in_main_thread(messagebox.showinfo, "Installer Launched", "The installer was launched. The application will now exit to allow installation.")
                        self.after(100, lambda: self.quit())
                    else:
                        self._run_in_main_thread(messagebox.showerror, "Update Error", "Failed to launch updater or installer. Please run the downloaded installer manually.")

                except Exception as dexc:
                    logger.exception(f"Update download/install failed: {dexc}")
                    self._run_in_main_thread(messagebox.showerror, "Update Error", f"Failed to download or launch installer: {dexc}")
                    try:
                        if os.path.exists(tmp_path):
                            os.remove(tmp_path)
                    except Exception:
                        pass

            except Exception as e:
                logger.error(f"Update check failed: {e}")
                self._run_in_main_thread(messagebox.showerror, "Update Error", "Could not check for updates. Please check your internet connection.")
            finally:
                self.after(0, lambda: self.update_btn.configure(state="normal", text="Check for Updates"))

        threading.Thread(target=run_check, daemon=True).start()

    def save_current_settings(self):
        settings = {
            "appearance_mode": self.appearance_mode,
            "save_dir": self.save_dir,
            "window_geometry": self.geometry(),
            "last_quality": self.quality_menu.get(),
            "last_type": self.type_menu.get(),
            "preferred_codec": self.codec_menu.get(),
            "post_action": self.post_action_menu.get(),
            "playlist_enabled": self.playlist_switch.get() == 1,
            "subtitles_enabled": self.sub_switch.get() == 1,
            "no_ffmpeg_enabled": self.compat_switch.get() == 1
        }
        # Advanced settings persisted
        try:
            settings["update_channel"] = self.update_channel_menu.get()
        except Exception:
            settings["update_channel"] = self.settings_mgr.get("update_channel", "stable")
        try:
            settings["telemetry_opt_in"] = self.telemetry_switch.get() == 1
        except Exception:
            settings["telemetry_opt_in"] = self.settings_mgr.get("telemetry_opt_in", False)
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