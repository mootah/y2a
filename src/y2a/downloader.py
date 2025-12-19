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

    video_exists    = os.path.exists(video_path)
    subtitle_exists = os.path.exists(subtitle_path)

    if config.get("is_dry"):
        if not subtitle_exists:
            ydl_opts["skip_download"] = True
        else:
            print("[cyan][INFO][/]", "Skipped. Already exists.")
            return
    elif "apkg" in config.get("formats"):
        if not video_exists:
            ydl_opts["format"] = video_format_id
        elif not subtitle_exists:
            ydl_opts["skip_download"] = True
        else:
            print("[cyan][INFO][/]", "Skipped. Already exists.")
            return
    else:
        if not subtitle_exists:
            ydl_opts["skip_download"] = True
        else:
            print("[cyan][INFO][/]", "Skipped. Already exists.")
            return

    url = f"https://www.youtube.com/watch?v={video_id}"

    try:
        with YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
    except Exception as e:
        print("[red][ERROR][/]", e)
        sys.exit(1)
