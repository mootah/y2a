import os, subprocess

from rich import print

def download(video_id: str, config):
    mp4_path = f"{video_id}/{video_id}.mp4"
    vtt_path = f"{video_id}/{video_id}.en-orig.vtt"

    cmd = [
        "yt-dlp",
        "-q", "--progress",
        "--write-auto-subs",
        "--sub-lang", "en.orig",
        "--sub-format", "vtt",
        "-o" "%(id)s/%(id)s.%(ext)s",
    ]

    if config["is_dry"]:
        cmd.append("--skip-download")
        if os.path.exists(vtt_path):
            print("[cyan][INFO][/]", "Skipped. Already exists.")
            return mp4_path, vtt_path
    else:
        cmd += ["-f", "18"]
        if os.path.exists(mp4_path):
            print("[cyan][INFO][/]", "Skipped. Already exists.")
            return mp4_path, vtt_path

    cmd.append(f"https://www.youtube.com/watch?v={video_id}")

    try:
        p = subprocess.run(cmd)
    except FileNotFoundError:
        print("[red][ERROR][/]", "Command not found: yt-dlp")
        exit(1)

    return mp4_path, vtt_path


