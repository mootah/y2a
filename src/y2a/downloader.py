import os, subprocess

from rich import print

def download(video_id: str, config):
    base_path = f"{video_id}/{video_id}"
    video_path  = base_path + ".mp4"
    subs_path  = base_path + ".en-orig.vtt"
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
    
    if not config["is_debug"]:
        cmd.append("-q")

    if config["is_dry"]:
        cmd.append("--skip-download")
        if os.path.exists(subs_path):
            print("[cyan][INFO][/]", "Skipped. Already exists.")
            return video_path, subs_path
    else:
        cmd += ["-f", video_format_id]
        if os.path.exists(video_path):
            print("[cyan][INFO][/]", "Skipped. Already exists.")
            return video_path, subs_path

    cmd.append(f"https://www.youtube.com/watch?v={video_id}")

    try:
        p = subprocess.run(cmd)
    except FileNotFoundError:
        print("[red][ERROR][/]", "Command not found: yt-dlp")
        exit(1)
    except Exception as e:
        print(e)
        exit(1)

    return video_path, subs_path


