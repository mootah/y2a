import os, sys, subprocess, multiprocessing, shutil
from concurrent.futures import ThreadPoolExecutor, as_completed
from rich import print
from rich.progress import track, Progress
import imageio_ffmpeg
from y2a.entity import Segment
from y2a.utils import get_media_filename

_FFMPEG_EXE = None

def get_ffmpeg_exe():
    """Return a path to an ffmpeg executable.

    Prefer the system ffmpeg (if available on PATH). Otherwise fall back
    to imageio_ffmpeg's bundled ffmpeg.
    """
    global _FFMPEG_EXE
    if _FFMPEG_EXE:
        return _FFMPEG_EXE

    # Prefer system-installed ffmpeg
    try:
        system_ffmpeg = shutil.which("ffmpeg")
    except Exception:
        system_ffmpeg = None

    if system_ffmpeg:
        _FFMPEG_EXE = system_ffmpeg
        return _FFMPEG_EXE

    # Fall back to imageio-ffmpeg
    _FFMPEG_EXE = imageio_ffmpeg.get_ffmpeg_exe()
    return _FFMPEG_EXE


def extract_audio(video_path, is_debug):
    print("[cyan][INFO][/]", "Extracting the entire audio...")
    audio_path = video_path.replace(".mp4", ".aac")
    # audio_path = video_path.replace(".mp4", ".wav")
    
    if os.path.exists(audio_path):
        print("[cyan][INFO][/]", "Skipped. Already exists.")
        return audio_path

    try:
        with Progress() as p:
            p.add_task("", total=None)
            # Select ffmpeg executable (system ffmpeg preferred)
            ffmpeg_path = get_ffmpeg_exe()

            cmd = [
                ffmpeg_path, "-y",
                "-i", video_path,
                "-vn",
                "-acodec", "copy",
                audio_path
            ]
            
            if not is_debug:
                cmd += ["-loglevel", "quiet"]
            
            subprocess.run(cmd, check=True)
    except Exception as e:
        print("[red][ERROR][/]", f"Failed to extract audio: {e}")
        sys.exit(1)

    return audio_path


def extract_seg_image(video_path, seg_image_path, ss, is_debug):
    ffmpeg_path = get_ffmpeg_exe()
    width = -2
    height = 320

    # Extract image frame

    # JPEG
    # cmd = [
    #     ffmpeg_path, "-y",
    #     "-ss", ss,
    #     "-i", video_path,
    #     "-frames:v", "1",
    #     "-q:v", "2",
    #     "-filter_complex", f"scale='min({width},iw)*sar':'min({height},ih)':out_color_matrix=bt601:out_range=pc",
    #     seg_image_path,
    # ]

    cmd = [
        ffmpeg_path, "-y",
        "-ss", ss,
        "-i", video_path,
        "-frames:v", "1",
        "-c:v", "libwebp",
        "-q:v", "80",
        "-filter_complex", f"scale='min({width},iw)*sar':'min({height},ih)':out_color_matrix=bt601:out_range=pc",
        seg_image_path,
    ]
    
    if not is_debug:
        cmd += ["-loglevel", "quiet"]
    
    subprocess.run(cmd, check=True)


def extract_seg_audio(audio_path, seg_audio_path, ss, t, is_debug):
    ffmpeg_path = get_ffmpeg_exe()

    # Extract audio segment

    # MP3
    # cmd = [
    #     ffmpeg_path, "-y",
    #     "-ss", ss, "-t", t,
    #     "-i", audio_path,
    #     "-ac", "1",
    #     "-c:a", "libmp3lame", "-b:a", "64k",
    #     "-map_metadata", "-1",
    #     seg_audio_path,
    # ]

    cmd = [
        ffmpeg_path, "-y",
        "-ss", ss, "-t", t,
        "-i", audio_path,
        "-ac", "1",
        "-c:a", "libopus", "-b:a", "64k",
        seg_audio_path,
    ]

    if not is_debug:
        cmd += ["-loglevel", "quiet"]
    
    subprocess.run(cmd, check=True)


def extract(segments: list[Segment], config):
    video_id   = config.get("video_id")
    video_path = config.get("video_path")
    is_debug   = config.get("is_debug")
    audio_ext  = config.get("audio_ext")
    image_ext  = config.get("image_ext")

    if config.get("is_dry"):
        print("[yellow][DRY][/]", "Skipped.")
        return []
    if not "apkg" in config.get("formats"):
        print("[cyan][INFO][/]", "Skipped.")
        return []

    audio_path = extract_audio(video_path, is_debug)

    out_dir = f"{video_id}/media"
    os.makedirs(out_dir, exist_ok=True)

    existing_files = set(os.listdir(out_dir))
    media_files = []

    tasks = []
    for seg in segments:
        start = seg.start
        end   = seg.end
        delta = seg.delta

        image_name = get_media_filename(video_id, start, end, image_ext)
        audio_name = get_media_filename(video_id, start, end, audio_ext)
        seg_image_path = os.path.join(out_dir, image_name)
        seg_audio_path = os.path.join(out_dir, audio_name)
        media_files.append(seg_image_path)
        media_files.append(seg_audio_path)

        ss = str(start.total_seconds())
        t = str(delta.total_seconds())

        if not image_name in existing_files:
            tasks.append((
                extract_seg_image,
                video_path, seg_image_path, ss, is_debug))
        
        if not audio_name in existing_files:
            tasks.append((
                extract_seg_audio,
                audio_path, seg_audio_path, ss, t, is_debug))

    cpu_count = multiprocessing.cpu_count()
    max_workers = max(1, min(cpu_count // 2, 4)) 

    print("[cyan][INFO][/]", "Extracting for each segment...")
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        try:
            futures = [ex.submit(*task) for task in tasks]

            for f in track(as_completed(futures), total=len(futures), description=""):
                try:
                    f.result()
                except Exception as e:
                    print("[red][ERROR][/]", "Extraction failed:", e)

        except KeyboardInterrupt:
            print("[red][ERROR][/]", "Shutting down...")
            ex.shutdown(wait=False, cancel_futures=True)
            sys.exit(1)

    return media_files
