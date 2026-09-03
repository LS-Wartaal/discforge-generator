import re
import subprocess

import yt_dlp

ALBUMS = """
ALBUMNAME:

- https://youtubeurlexample1
- https://youtubeurlexample2

"""

def parse_albums(text):
    albums = {}
    current_album = None

    for line in text.splitlines():
        line = line.strip()

        if not line:
            continue

        # URL line
        if line.startswith("-"):
            if current_album is None:
                continue

            url = line[1:].strip()

            if url:
                albums[current_album].append(url)

            continue

        if line.endswith(":"):
            current_album = line[:-1].strip()

            if current_album:
                albums.setdefault(current_album, [])

    return albums


def sanitize_filename(name):

    name = re.sub(r'[<>:"/\\|?*]', "_", name)
    name = re.sub(r"\s+", " ", name)
    return name.strip(" .")


def download_album(album_name, urls):
    global temp_dir
    album_dir = sanitize_filename(album_name)
    album_dir.mkdir(parents=True, exist_ok=True)

    print()
    print("=" * 60)
    print(f"Album: {album_name}")
    print(f"Output: {album_dir}")
    print("=" * 60)

    for url in urls:
        print()
        print(f"Downloading: {url}")

        temp_dir = album_dir / ".tmp"
        temp_dir.mkdir(parents=True, exist_ok=True)

        ydl_opts = {
            "format": "bestaudio/best",

            "js_runtimes": {
                "deno": {
                    "path": r"C:\Users\leons\AppData\Roaming\Python\Python310\Scripts\deno.exe"
                }
            },

            "outtmpl": str(temp_dir / "%(title)s.%(ext)s"),
            "noplaylist": True,

            "postprocessors": [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "320",
                }
            ],

            "quiet": False,
            "no_warnings": False,

        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)

                title = info.get("title", "unknown")

        except Exception as e:
            print(f"ERROR downloading {url}: {e}")
            continue

        title = sanitize_filename(title)

        mp3_path = temp_dir / f"{title}.mp3"
        ogg_path = album_dir / f"{title}.ogg"

        if not mp3_path.exists():
            mp3_files = list(temp_dir.glob("*.mp3"))

            if not mp3_files:
                print(f"ERROR: Could not find MP3 for: {title}")
                continue

            mp3_path = max(
                mp3_files,
                key=lambda p: p.stat().st_mtime
            )

        print(f"Converting:")
        print(f"  {mp3_path}")
        print(f"  -> {ogg_path}")

        try:
            subprocess.run(
                [
                    "ffmpeg",
                    "-y",
                    "-i",
                    str(mp3_path),
                    "-c:a",
                    "libvorbis",
                    "-q:a",
                    "6",
                    str(ogg_path),
                ],
                check=True,
            )

        except FileNotFoundError:
            print(
                "ERROR: ffmpeg was not found. "
                "Install ffmpeg and make sure it is on PATH."
            )
            return

        except subprocess.CalledProcessError as e:
            print(f"ERROR converting {title}: {e}")
            continue

        try:
            mp3_path.unlink()
        except OSError:
            pass

        print(f"Done: {ogg_path}")

    try:
        temp_dir.rmdir()
    except OSError:
        pass


def main():
    albums = parse_albums(ALBUMS)

    if not albums:
        print("No albums found.")
        return

    for album_name, urls in albums.items():
        if not urls:
            print(f"Skipping '{album_name}': no URLs.")
            continue

        download_album(album_name, urls)

    print()
    print("All albums finished.")


if __name__ == "__main__":
    main()
