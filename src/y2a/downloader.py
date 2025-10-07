import os, subprocess

from rich import print

def download(video_id: str):
    mp4_out = f"{video_id}/{video_id}.mp4"
    if not os.path.exists(mp4_out):
        try:
            p = subprocess.run([
                "yt-dlp",
                "-q", "--progress",
                "--write-auto-subs",
                "--sub-lang", "en.orig",
                "--sub-format", "vtt",
                "-f", "18",
                "-o" "%(id)s/%(id)s.%(ext)s",
                f"https://www.youtube.com/watch?v={video_id}"
            ])
        except FileNotFoundError:
            print("[red][ERROR][/]", "Command not found: yt-dlp")
            exit(1)
    else:
        print("[cyan][INFO][/]", "Skipped. Already exists.")


