import os, re, csv, json, collections
from datetime import timedelta
from importlib import import_module
from importlib.metadata import version, PackageNotFoundError

from rich import print
from rich.progress import Progress
import spacy
from spacy.tokens import DocBin
from spacy.tokens.doc import Doc

from y2a.entity import Segment


def get_version():
    try:
        return version("y2a")
    except PackageNotFoundError:
        return "0.0.0"

def load_spacy(model_name: str, **kwargs) -> spacy.Language:
    try:
        model_module = import_module(model_name)
    except ModuleNotFoundError:
        spacy.cli.download(model_name)
        model_module = import_module(model_name)

    return model_module.load(**kwargs)


def get_spacy_document(text: str, config) -> Doc:
    video_id = config.get("video_id")
    file_path = f"{video_id}/{video_id}.spacy"
    nlp = load_spacy("en_core_web_sm")

    print("[cyan][INFO][/]", "Analyzing text...")
    if os.path.exists(file_path):
        print("[cyan][INFO][/]", "Skipped. Spacy document found.")
        loaded_bin = DocBin().from_disk(file_path)
        doc = list(loaded_bin.get_docs(nlp.vocab))[0]
        return doc

    doc = None
    with Progress() as p:
        p.add_task("", total=None)
        doc = nlp(text)

    if "spacy" in config.get("formats"):
        docbin = DocBin()
        docbin.add(doc)
        docbin.to_disk(file_path)
        print("[cyan][INFO][/]", f"[green]File created: {file_path}")

   
    return doc

def parse_time(srt_time: str) -> timedelta:
    """
    "HH:mm:ss.mmm" -> timedelta
    """
    h, m, rest = srt_time.split(":")
    s, ms = re.split(r'[,\.]', rest)
    return timedelta(
        hours=int(h),
        minutes=int(m),
        seconds=int(s),
        milliseconds=int(ms)
    )


def format_time(td: timedelta, delim: str = ".") -> str:
    """
    timedelta -> HH.mm.ss.mmm
    """
    total_ms = int(td.total_seconds() * 1000)
    hours, rest = divmod(total_ms, 3600 * 1000)
    minutes, rest = divmod(rest, 60 * 1000)
    seconds, millis = divmod(rest, 1000)
    return f"{hours:02}{delim}{minutes:02}{delim}{seconds:02}.{millis:03}"


def get_note_id(video_id, start, end):
    start_str = format_time(start)
    end_str = format_time(end)
    return f"{video_id}_{start_str}-{end_str}"


def get_media_filename(video_id, start, end, ext):
    note_id = get_note_id(video_id, start, end)
    return f"y2a-{note_id}.{ext}"


def write_in_vtt(file_path: str, segments: list[Segment]):
    """
    vtt output
    """
    output = [
        "WEBVTT",
        "Kind: captions",
        "Language: en\n",
    ]
    for segment in segments:
        start = segment.start
        end = segment.end
        sentence = segment.sentence
        start_str = format_time(start, delim=":")
        end_str = format_time(end, delim=":")
        output.append(f"{start_str} --> {end_str}")
        # output.append(f"{sentence}")
        output.append(f"{sentence}\n")

    with open(file_path, "w", encoding="utf-8") as f:
        for row in output:
            f.write(row + "\n")

    print("[cyan][INFO][/]", f"[green]File created: {file_path}")


def write_in_txt(file_path: str, segments: list[Segment]):
    """
    txt output
    """
    sents = [seg.sentence for seg in segments]
    with open(file_path, "w", encoding="utf-8") as f:
        for s in sents:
            f.write(s + "\n")

    print("[cyan][INFO][/]", f"[green]File created: {file_path}")


def write_in_csv(file_path: str, rows: list[str]):
    """
    csv output
    """
    with open(file_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, delimiter="\t")
        for row in rows:
            writer.writerow(row)

    print("[cyan][INFO][/]", f"[green]File created: {file_path}")


def write_in_json(file_path: str, rows: list[str]):
    """
    json output
    """
    with open(file_path, mode="w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=4)

    print("[cyan][INFO][/]", f"[green]File created: {file_path}")


def print_segment(segment: Segment):
    print(
        "[magenta][VERBOSE][/]",
        segment.delta.total_seconds(), "seconds,",
        len(segment), "words"
    )
    print("[magenta][VERBOSE][/]", segment.sentence)


def print_longest_segment(segments: list[Segment]):
    time_wise = None
    word_wise = None
    max_duration = timedelta(seconds=0)
    max_length = 0
    for seg in segments:
        duration = seg.delta
        if duration > max_duration:
            max_duration = duration
            time_wise = seg
        length = len(seg)
        if length > max_length:
            max_length = length
            word_wise = seg

    print()
    print("[magenta][VERBOSE][/]", "Longest segment (duration)")
    if time_wise:
        print_segment(time_wise)

    print()
    print("[magenta][VERBOSE][/]", "Longest segment (words)")
    if word_wise:
        print_segment(word_wise)

    print()


def print_token_count(doc: Doc):
    tokens = [str(token) for token in doc if not token.is_space]
    lemmas = [token.lemma_.lower() for token in doc if token.is_alpha]
    
    token_freq = collections.Counter(tokens).most_common()
    lemma_freq = collections.Counter(lemmas).most_common()

    print()
    print("[magenta][VERBOSE][/]", f"{len(tokens):,} tokens", f"({len(token_freq):,} unique)")
    print("[magenta][VARBOSE][/]", f"{len(lemmas):,} lemmas", f"({len(lemma_freq):,} unique)")
    print()


def print_summary(segments: list[Segment], config):
    durations = [seg.delta for seg in segments]
    
    max_seconds = int(config.get("max_duration").total_seconds())
    duration_counts = [0 for _ in range(max_seconds)]
    over_max_sec = 0
    
    for d in durations:
        found = False
        for i in range(len(duration_counts)):
            if d <= timedelta(seconds=i+1):
                duration_counts[i] += 1
                found = True
                break
        if not found:
            over_max_sec += 1

    print()
    for i, d in enumerate(duration_counts):
        print("[magenta][VERBOSE][/]", f"~ {i+1} sec: {d:,} segments")
    print("[magenta][VERBOSE][/]", f"{max_seconds} sec ~: {over_max_sec:,} segments")

    total = sum(durations, timedelta())
    print()
    print("[magenta][VERBOSE][/]", f"{format_time(total, delim=':')} in total.")
    