import os, sys
from rich import print
from yt_dlp import YoutubeDL


def download(video_id: str, config):
    video_path = config.get("video_path")
    subtitle_path = config.get("subtitle_path")
    video_format_id = "18"

    ydl_opts = {
        "progress": True,
        "writesubtitles": True,
        "writeautomaticsub": True, # --write-auto-subs
        "subtitleslangs": ["en.orig"],
        "subtitlesformat": "srv2",
        "outtmpl": "%(id)s/%(id)s.%(ext)s", # -o
    }

    # --quiet
    if not config.get("is_debug"):
        ydl_opts["quiet"] = True

    # --skip-download
    if config.get("is_dry") or "apkg" not in config.get("formats"):
        ydl_opts["skip_download"] = True
        if os.path.exists(subtitle_path):
            print("[cyan][INFO][/]", "Skipped. Subtitle already exists.")
            return
    else:
        ydl_opts["format"] = video_format_id
        if os.path.exists(video_path):
            print("[cyan][INFO][/]", "Skipped. Video already exists.")
            return

    url = f"https://www.youtube.com/watch?v={video_id}"

    try:
        with YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
    except Exception as e:
        print("[red][ERROR][/]", e)
        sys.exit(1)
