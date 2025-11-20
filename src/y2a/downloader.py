import os, sys, subprocess

from rich import print

def download(video_id: str, config):
    video_path = config.get("video_path")
    subtitle_path = config.get("subtitle_path")
    video_format_id = "18"
    # video_format_id = "92"

    cmd = [
        "yt-dlp",
        "--progress",
        "--write-auto-subs",
        "--sub-lang", "en.orig",
        "--sub-format", "vtt",
        "-o", "%(id)s/%(id)s.%(ext)s",
    ]
    
    if not config.get("is_debug"):
        cmd.append("-q")

    if config.get("is_dry") or not "apkg" in config.get("formats"):
        cmd.append("--skip-download")
        if os.path.exists(subtitle_path):
            print("[cyan][INFO][/]", "Skipped. Already exists.")
            return
    else:
        cmd += ["-f", video_format_id]
        if os.path.exists(video_path):
            print("[cyan][INFO][/]", "Skipped. Already exists.")
            return

    cmd.append(f"https://www.youtube.com/watch?v={video_id}")

    try:
        p = subprocess.run(cmd)
    except FileNotFoundError:
        print("[red][ERROR][/]", "Command not found: yt-dlp")
        sys.exit(1)
    except Exception as e:
        print(e)
        sys.exit(1)



