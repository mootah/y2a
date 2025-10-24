import os, argparse
from datetime import timedelta

from rich import print

from .utils import write_in_vtt
from .downloader import download
from .processor import convert_subs_into_lines
from .extractor import extract_media
from .generator import generate_apkg


def main():
    parser = argparse.ArgumentParser(
        description="Create a Anki deck from a YouTube video.")
    parser.add_argument(
        "-i", default="",
        help="video id")
    parser.add_argument(
        "--mp4", default="",
        help="mp4 file path")
    parser.add_argument(
        "--vtt", default="",
        help="vtt file path (default: <video_name>.en-orig.vtt)")
    parser.add_argument(
        "--archive", default="",
        help="txt file path. a list of archived sentences")
    parser.add_argument(
        "--no_archive_update", action="store_true",
        help="not update the archive file (default: False)")
    parser.add_argument(
        "--make_txt", action="store_true",
        help="create a txt file (default: False)")
    parser.add_argument(
        "--make_vtt", action="store_true",
        help="create a vtt file (default: False)")
    parser.add_argument(
        "--make_tsv", action="store_true",
        help="create a tsv file (default: False)")
    parser.add_argument(
        "--make_json", action="store_true",
        help="create a json file (default: False)")
    parser.add_argument(
        "--make_spacy", action="store_true",
        help="create a spacy document binary (default: False)")
    parser.add_argument(
        "--dry", action="store_true",
        help="dry run (default: False)")
    parser.add_argument(
        "--verbose", action="store_true",
        help="print verbosely (default: False)")
    parser.add_argument(
        "--debug", action="store_true",
        help="debug mode (default: False)")
    parser.add_argument(
        "--cut", default="comma,pause",
        help="cutting sentences by (comma, pause) (default: \"comma,pause\")")
    parser.add_argument(
        "--keep_dups", action="store_true",
        help="keep duplicate sentences (default: False)")
    parser.add_argument(
        "--max_duration", default=12, type=int,
        help="maximum duration to cut (seconds) (default: 12)")
    parser.add_argument(
        "--min_words", default=8, type=int,
        help="minimum words length to cut (default: 8)")
    parser.add_argument(
        "--pad_start", default=100, type=int,
        help="padding for start timing of a line (milliseconds) (default: 100)")
    parser.add_argument(
        "--pad_end", default=25, type=int,
        help="padding for end timing of a line (milliseconds) (default: 25)")

    args = parser.parse_args()

    config = {
        "video_id":          args.i,
        "video_path":        args.mp4,
        "subs_path":         args.mp4.replace(".mp4", ".en-orig.vtt"),
        "is_dry":            args.dry,
        "is_verbose":        args.verbose,
        "is_debug":          args.debug,
        "makes_txt":         args.make_txt,
        "makes_vtt":         args.make_vtt,
        "makes_tsv":         args.make_tsv,
        "makes_json":        args.make_json,
        "makes_spacy":       args.make_spacy,
        "archive_path":      args.archive,
        "no_archive_update": args.no_archive_update,
        "cutting":           args.cut,
        "keeps_dups":        args.keep_dups,
        "duration_limit":    timedelta(seconds=args.max_duration),
        "words_limit":       args.min_words,
        "pad_start":         timedelta(milliseconds=args.pad_start),
        "pad_end":           timedelta(milliseconds=args.pad_end),
    }


    if not config["video_id"] and not config["video_path"]:
        print("[red][ERROR][/]", "You need to provide video_id or video_path.")
        exit(1)

    if not config["video_id"] and config["video_path"]:
        config["video_id"], _ = os.path.splitext(os.path.basename(config["video_path"]))

    os.makedirs(config["video_id"], exist_ok=True)

    if config["video_id"] and not config["video_path"]:
        print()
        print("[green][TASK] [0/3][/]", "Downloading the video and its subtitle...")
        config["video_path"], config["subs_path"] = download(config["video_id"], config)

    if args.vtt:
        config["subs_path"] = args.vtt

    print()
    print("[green][TASK] [1/3][/]", "Converting subs into segments...")
    lines = convert_subs_into_lines(config["subs_path"], config)
    print()
    print("[green][TASK] [2/3][/]", "Extracting media files...")
    media = extract_media(lines, config)
    print()
    print("[green][TASK] [3/3][/]", "Generating Anki package...")
    generate_apkg(lines, media, config)


