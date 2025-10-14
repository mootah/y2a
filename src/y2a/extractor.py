import os, subprocess, random

from rich import print
from rich.progress import track

from .types import Line
from .utils import format_time

def extract_media(lines: list[Line], config):
    video_id = config["video_id"]
    video_path = config["video_path"]

    if config["is_dry"]:
        print("[yellow][DRY][/]", "Skipped.")
        return []

    out_dir = f"{video_id}/media"
    os.makedirs(out_dir, exist_ok=True)

    media_files = []

    for start, end, sentence in track(lines, description="Extracting", total=len(lines)):
        start_str = format_time(start)
        end_str = format_time(end)

        duration = (end - start).total_seconds()

        base_name = f"{video_id}_{start_str}-{end_str}"

        width = -2
        height = 320

        # jpg
        img_path = os.path.join(out_dir, f"{base_name}.jpg")
        if not os.path.exists(img_path):
            try:
                cmd = [
                    "ffmpeg", "-y",
                    "-ss", str(start.total_seconds()),
                    "-i", video_path,
                    "-filter_complex",
                    f"scale=iw*sar:ih,scale='min({width},iw)*sar':'min({height},ih)':out_color_matrix=bt601:out_range=pc",
                    "-vframes", "1",
                    "-qscale:v", "2",
                ]

                if not config["is_debug"]:
                    cmd += ["-loglevel", "quiet"]

                cmd.append(img_path)

                p = subprocess.run(cmd)
            except FileNotFoundError:
                print("[red][ERROR][/]", "Command not found: ffmpeg")
                exit(1)
        media_files.append(img_path)

        # mp3
        audio_path = os.path.join(out_dir, f"{base_name}.mp3")
        if not os.path.exists(audio_path):
            try:
                cmd = [
                    "ffmpeg", "-y",
                    "-ss", str(start.total_seconds()),
                    "-t", str(duration),
                    "-i", video_path,
                    "-loglevel", "quiet",
                    "-sn",
                    "-map_metadata", "-1",
                    "-vn",
                    "-ac","1",
                    "-c:a", "libmp3lame",
                    "-b:a", "64",
                ]

                if not config["is_debug"]:
                    cmd += ["-loglevel", "quiet"]

                cmd.append(audio_path)

                p = subprocess.run(cmd)
            except FileNotFoundError:
                print("[red][ERROR][/]", "Command not found: ffmpeg")
                exit(1)
        media_files.append(audio_path)

    return media_files
