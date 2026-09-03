from pathlib import Path
import subprocess
import os


ROOT_DIR = Path("yt-dlp")


def convert_to_mono(ogg_path):
    print(f"Converting: {ogg_path}")

    temp_path = ogg_path.with_suffix(".mono.tmp.ogg")

    try:
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-fflags",
                "+genpts",
                "-i",
                str(ogg_path),
                "-ac",
                "1",
                "-c:a",
                "libvorbis",
                "-q:a",
                "6",
                str(temp_path),
            ],
            check=True,
        )

        os.replace(temp_path, ogg_path)

        print(f"Done: {ogg_path}")

    except subprocess.CalledProcessError:
        print(f"ERROR converting: {ogg_path}")

        if temp_path.exists():
            temp_path.unlink()


def main():
    if not ROOT_DIR.exists():
        print(f"Directory not found: {ROOT_DIR}")
        return

    ogg_files = list(ROOT_DIR.rglob("*.ogg"))

    print(f"Found {len(ogg_files)} OGG files.")

    for ogg_file in ogg_files:
        convert_to_mono(ogg_file)

    print()
    print("All files converted to mono.")


if __name__ == "__main__":
    main()
