import os, re, csv, json, collections
from datetime import timedelta
from importlib import import_module

from rich import print
from rich.progress import Progress
import spacy
from spacy.tokens import DocBin
from spacy.tokens.doc import Doc

from .types import Line, Segment


def load_spacy(model_name: str, **kwargs) -> spacy.Language:
    try:
        model_module = import_module(model_name)
    except ModuleNotFoundError:
        spacy.cli.download(model_name)
        model_module = import_module(model_name)

    return model_module.load(**kwargs)


def get_spacy_document(text: str, config) -> Doc:
    video_id = config["video_id"]
    file_path = f"{video_id}/{video_id}.spacy"
    nlp = load_spacy("en_core_web_sm")

    if os.path.exists(file_path):
        print("[cyan][INFO][/]", "Loading spacy documents...")
        loaded_bin = DocBin().from_disk(file_path)
        doc = list(loaded_bin.get_docs(nlp.vocab))[0]
        return doc

    print("[cyan][INFO][/]", "Analyzing text...")
    doc = None
    with Progress() as p:
        p.add_task("Analyzing", total=None)
        doc = nlp(text)

    if config["makes_spacy"]:
        docbin = DocBin()
        docbin.add(doc)
        docbin.to_disk(file_path)
   
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


def write_in_vtt(file_path: str, lines: list[Line]):
    """
    vtt output
    """
    output = []
    for start, end, sentence in lines:
        start_str = format_time(start, delim=":")
        end_str = format_time(end, delim=":")
        output.append(f"{start_str} --> {end_str}")
        output.append(f"{sentence}")
        output.append(f"{sentence}\n")

    with open(file_path, "w", encoding="utf-8") as f:
        for row in output:
            f.write(row + "\n")

    print("[cyan][INFO][/]", f"vtt created: {file_path}")


def write_in_tsv(file_path: str, rows: list[str]):
    """
    tsv output
    """
    with open(file_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, delimiter="\t")
        for row in rows:
            writer.writerow(row)

    print("[cyan][INFO][/]", f"tsv created: {file_path}")


def write_in_json(file_path: str, rows: list[str]):
    """
    json output
    """
    with open(file_path, mode="w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=4)

    print("[cyan][INFO][/]", f"json created: {file_path}")


def print_segment(segment: Segment):
    print(
        "[magenta][VERBOSE][/]",
        (segment[-1][1] - segment[0][0]).total_seconds(), "seconds,",
        len(segment), "words"
    )
    print("[magenta][VERBOSE][/]", " ".join([w for _, _, w in segment]))


def print_longest_segment(segments: list[Segment]):
    time_wise = []
    word_wise = []
    max_duration = timedelta(seconds=0)
    max_length = 0
    for seg in segments:
        duration = seg[-1][1] - seg[0][0]
        if duration > max_duration:
            max_duration = duration
            time_wise = seg
        length = len(seg)
        if length > max_length:
            max_length = length
            word_wise = seg

    print()
    print("[magenta][VERBOSE][/]", "Longest segment (duration)")
    print_segment(time_wise)

    print()
    print("[magenta][VERBOSE][/]", "Longest segment (words)")
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




