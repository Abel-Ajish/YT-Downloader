# YouTube Audio/Video Downloader

[![Build Status](https://img.shields.io/badge/build-passing-brightgreen)](https://github.com/Abel-Ajish/YT-Downloader)
[![Version](https://img.shields.io/badge/version-1.0.4-blue)](https://github.com/Abel-Ajish/YT-Downloader/releases)
[![Downloads](https://img.shields.io/badge/downloads-view-orange)](https://github.com/Abel-Ajish/YT-Downloader/releases)

A production-ready, high-performance YouTube downloader with a modern UI, built with Python, CustomTkinter, and yt-dlp.

## 🚀 Features

- **High-Quality Downloads**: Supports up to 4K resolution and high-bitrate audio.
- **Multiple Formats**: Download as Video (.MP4/.MKV), Audio Only (.MP3/.M4A), or Thumbnail Only (.JPG).
- **Playlist Support**: Download entire playlists with a single click.
- **Subtitle Embedding**: Automatically fetch and embed English subtitles into videos.
- **Modern UI**: Clean, responsive interface with Light and Dark mode support.
- **Dependency Management**: Automated first-run FFmpeg validation and installation.
- **Robust Error Handling**: Comprehensive logging and user-friendly error reporting.
- **Persistence**: Remembers your preferred save location, theme, and window size.
- **Keyboard Shortcuts**:
  - `Ctrl + S`: Start download
  - `Ctrl + O`: Change save folder

## 🚀 Quick Start

For the easiest experience, download the **Standalone Installer**:

1. Go to the [Releases](https://github.com/Abel-Ajish/YT-Downloader/releases) page.
2. Download `Setup-YTDownloader.exe`.
3. Run the file. It's a native Windows installer that handles everything for you.

### 🪟 What the Installer Does:
- **No Python? No Problem**: It automatically detects if Python is missing and installs it for you.
- **Always Up-to-Date**: It downloads the latest binaries directly from GitHub.
- **Easy Access**: Creates a Desktop shortcut and a Start Menu entry.
- **Clean Removal**: Includes a built-in uninstaller.

### 🍎 macOS & 🐧 Linux
1. Download the standalone executable for your OS from the [Releases](https://github.com/user/yt-downloader/releases) page.
2. Grant execution permissions:
   ```bash
   chmod +x YT-Downloader
   ```
3. Run the application. On the first launch, it will perform a dependency audit for **FFmpeg**.

## 🏗️ Build Instructions

### Building the Main App
To build the standalone executable for your current OS:
```bash
pyinstaller YT-Downloader.spec
```

### Building the Windows Installer
To build the bootstrap installer (Windows only):
```bash
pip install winshell pywin32
pyinstaller Setup.spec
```

## 🗑️ Uninstallation

- **Windows**: Use the "Uninstall" shortcut in the application folder or run the uninstaller from the settings.
- **macOS/Linux**: Simply delete the executable and the configuration folder at `~/.yt_downloader`.
- **Conversions failing?** Ensure FFmpeg is installed correctly. You can enable "No-FFmpeg Safe Fallback" in the settings.
- **Slow downloads?** Check your internet connection or try updating the app (if a new version is available).
- **App not opening?** Check the logs at `~/.yt_downloader/logs/app.log`.

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📄 License

Distributed under the MIT License. See `LICENSE` for more information.

## 🙌 Credits

- [yt-dlp](https://github.com/yt-dlp/yt-dlp) - The core download engine.
- [CustomTkinter](https://github.com/TomSchimansky/CustomTkinter) - Modern UI components.
- [FFmpeg](https://ffmpeg.org/) - Multimedia framework.
