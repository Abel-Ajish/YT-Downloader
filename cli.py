import argparse
import os
import sys
import yt_dlp
from utils import sanitize_filename


def main():
    p = argparse.ArgumentParser(description="YT-Downloader CLI (headless)")
    p.add_argument('url', help='YouTube video or playlist URL')
    p.add_argument('--output-dir', '-o', default=os.path.join(os.path.expanduser('~'), 'Downloads'))
    p.add_argument('--audio', action='store_true', help='Download audio only')
    p.add_argument('--thumbnail', action='store_true', help='Download thumbnail only')
    p.add_argument('--retries', type=int, default=2, help='Number of attempts before failing')

    args = p.parse_args()

    url = args.url
    out_dir = os.path.abspath(args.output_dir)
    os.makedirs(out_dir, exist_ok=True)

    # First extract metadata
    meta_opts = {'quiet': True, 'no_warnings': True, 'skip_download': True}
    try:
        with yt_dlp.YoutubeDL(meta_opts) as ydl:
            info = ydl.extract_info(url, download=False)
    except Exception as e:
        print(f"Failed to fetch metadata: {e}")
        sys.exit(2)

    title = info.get('title', 'untitled')
    safe_title = sanitize_filename(title)

    # Build download options
    ydl_opts = {
        'outtmpl': os.path.join(out_dir, safe_title + '.%(ext)s'),
        'noplaylist': True if not info.get('entries') else False,
    }

    if args.thumbnail:
        ydl_opts.update({'skip_download': True, 'writethumbnail': True})
    elif args.audio:
        ydl_opts.update({'format': 'bestaudio/best', 'postprocessors': [{'key':'FFmpegExtractAudio','preferredcodec':'mp3','preferredquality':'192'}]})

    attempt = 1
    while attempt <= args.retries:
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
            # basic verification: check for files matching safe_title
            found = False
            for f in os.listdir(out_dir):
                if f.startswith(safe_title):
                    path = os.path.join(out_dir, f)
                    if os.path.getsize(path) > 0:
                        print(f"Downloaded: {path}")
                        found = True
                        break
            if not found:
                raise IOError("Downloaded file missing or empty")
            sys.exit(0)
        except Exception as e:
            print(f"Attempt {attempt} failed: {e}")
            attempt += 1

    print(f"All {args.retries} attempts failed.")
    sys.exit(1)


if __name__ == '__main__':
    main()
