import os, sys
from datetime import timedelta
from rich import print
import rich_click as click

from y2a.downloader import download
from y2a.parser import parse
from y2a.extractor import extract
from y2a.generator import generate
from y2a.utils import (
    get_version,
    write_in_vtt,
    write_in_txt,
    write_in_csv,
    write_in_json
)

FORMATS = ("apkg", "csv", "json", "vtt", "txt", "spacy")
BOUNDARIES = ("sentence", "grammar", "speech", "all")
CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help'])

def parse_video_string(video_string):
    video_id = ""
    video_path = ""
    if video_string.endswith(".mp4"):
        video_path = video_string
        video_id = os.path.splitext(os.path.basename(video_path))
    elif len(video_string) == 11:
        video_id = video_string
        video_path = f"{video_id}/{video_id}.mp4"
    else:
        print("[red][ERROR][/]", "ID must be an 11-digit string.")
        sys.exit(1)
        
    return video_id, video_path


@click.command(context_settings=CONTEXT_SETTINGS,
    help="Convert YouTube video into Anki deck")
@click.version_option(
    get_version(),
    "-v", "--version",
    prog_name="y2a"
)
@click.argument("video",
    help="video ID or video filepath (.mp4)",
    metavar="ID|PATH")
@click.option("--subtitle", "-s",
    help="subtitle filepath (.srv2)",
    type=click.Path())
@click.option("--format", "-f", default=["apkg"],
    help="output format (multi: -f ... -f ...)",
    multiple=True, show_default=True,
    type=click.Choice(FORMATS, case_sensitive=False))
@click.option("--max_duration", "-d", default=8000,
    help="max duration (in ms) for each segment",
    type=int, show_default=True)
@click.option("--min_words", "-w", default=3,
    help="min number of words for each segment",
    type=int, show_default=True)
@click.option("--margin", "-m", default=(100, 25),
    help="audio margins (in ms) for each segment",
    type=(int, int), metavar="START END", show_default=True)
@click.option("--boundary", "-b", default=["all"],
    help="boundary types used to split the text (multi: -b ... -b ...)",
    multiple=True, show_default=True,
    type=click.Choice(BOUNDARIES, case_sensitive=False))
@click.option("--keep_dups", is_flag=True,
    help="prevent removing duplicated lines")
@click.option("--dry", is_flag=True,
    help="run without video DL and file creation")
@click.option("--verbose", "-V", is_flag=True,
    help="run verbosely")
@click.option("--debug", "-D", is_flag=True,
    help="run in debug mode")
def main(video, **args):
    video_id, video_path = parse_video_string(video)
    subtitle_path = video_path.replace(".mp4", ".en-orig.srv2")
    subtitle_path = args.get("subtitle") or subtitle_path
    
    boundaries = args.get("boundary")
    if "all" in boundaries:
        boundaries = ("sentence", "grammar", "speech")

    config = {
        "video_id": video_id,
        "video_path": video_path,
        "subtitle_path": subtitle_path,
        "formats": args.get("format"),
        "boundaries": boundaries,
        "should_keep_dups": args.get("keep_dups"),
        "max_duration": timedelta(milliseconds=args.get("max_duration")),
        "min_words": args.get("min_words"),
        "margin_start": timedelta(milliseconds=args.get("margin")[0]),
        "margin_end": timedelta(milliseconds=args.get("margin")[1]),
        "is_dry": args.get("dry"),
        "is_verbose": args.get("verbose"),
        "is_debug": args.get("debug")
    }

    if config.get("is_debug"):
        print(config)

    print()
    print("[green][TASK] [0/3][/]", "Downloading the video and subtitle...")
    if not os.path.exists(video_id):
        os.makedirs(video_id, exist_ok=True)
    download(video_id, config)

    print()
    print("[green][TASK] [1/3][/]", "Parsing the subtitle into segments...")
    segments = parse(subtitle_path, config)

    if "vtt" in config.get("formats") and not config.get("is_dry"):
        write_in_vtt(f"{video_id}/{video_id}.out.vtt", segments)

    if "txt" in config.get("formats") and not config.get("is_dry"):
        write_in_txt(f"{video_id}/{video_id}.txt", segments)

    print()
    print("[green][TASK] [2/3][/]", "Extracting media files...")
    media = extract(segments, config)

    print()
    print("[green][TASK] [3/3][/]", "Generating an Anki package...")
    cards = generate(segments, media, config)

    if "csv" in config.get("formats") and not config.get("is_dry"):
        rows = [c.values() for c in cards]
        write_in_csv(f"{video_id}/{video_id}.csv", rows)

    if "json" in config.get("formats") and not config.get("is_dry"):
        write_in_json(f"{video_id}/{video_id}.json", cards)


if __name__ == "__main__":
    main()