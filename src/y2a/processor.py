import os, subprocess, re
from datetime import timedelta
from importlib import import_module

from rich import print
from rich.progress import track
from spacy.tokens.doc import Doc

from .types import TimedWord, Segment, Line
from .utils import (
    load_spacy,
    parse_time,
    format_time,
    write_in_vtt,
    print_longest_segment,
    print_token_count,
    print_segment
)


def convert_subs_into_words(subs: list[str]) -> list[TimedWord]:
    timed_words = []
    i = 0
    while i < len(subs):
        row = subs[i].strip()
        if re.match(r"^\d\d:\d\d:\d\d\.\d+ -->", row):

            # time
            time_row = row
            start, end = time_row.split(" --> ")
            end = end.replace(" align:start position:0%", "")

            # word (the next next row)
            i += 2
            if i < len(subs):
                word_row = subs[i].strip()
            else:
                word_row = ""

            head_word = word_row.split("<")[0].strip()

            times = [parse_time(start)]
            words = [head_word]
            pattern = re.compile(r"<(\d+:\d+:\d+\.\d+)>.*?<c>(.*?)</c>")
            for t, w in pattern.findall(word_row):
                times.append(parse_time(t))
                words.append(w.strip())
            times.append(parse_time(end))

            for j, word in enumerate(words):
                word_start = times[j]
                word_end   = times[j + 1]

                word = word.replace("&gt;&gt; ", "")

                if not word:
                    continue
                if word.startswith("["):
                    continue

                # 単語あたりの最大の時間
                max_word_delta = timedelta(seconds=2)
                if " " in word:
                    pass
                elif word_end - word_start > max_word_delta:
                    word_end = word_start + max_word_delta
                timed_words.append((word_start, word_end, word))
        i += 1

    print("[cyan][INFO][/]", f"{len(timed_words):,} words found.")

    return timed_words


def convert_words_into_segments(doc: Doc, timed_words: list[TimedWord]) -> list[Segment]:
    words = [w for _, _, w in timed_words]
    sentences = [sent.text.strip() for sent in doc.sents]

    pos = 0
    segments = []
    for sent in sentences:
        cnt = 0
        for i in range(1, len(words[pos:]) + 1):
            part = " ".join(words[pos:pos+i])
            if not part in sent:
                break
            cnt = i
        seg = list(timed_words[pos:pos+cnt])
        if len(seg):
            segments.append(seg)
        pos += cnt

    return segments


def split_by_jump(segment: Segment, config) -> list[Segment]:
    """
    タイムスタンプの切れ目で分割する
    """
    segments = []
    current_seg = []
    length = len(segment)

    for i, (start, end, word) in enumerate(segment):
        current_seg.append((start, end, word))
        if i + 1 < length and segment[i + 1][0] - end > timedelta(seconds=2):
            segments.append(current_seg)
            current_seg = []
    if current_seg:
        segments.append(current_seg)

    return segments


def split_by_pause(segment: Segment, config) -> list[Segment]:
    """
    単語間の時間が最も長い箇所で分割する
    """

    if len(segment) < config["words_limit"]:
        return [segment]

    seg_start = segment[0][0]
    seg_end   = segment[-1][1]
    seg_delta = seg_end - seg_start

    if seg_delta < config["duration_limit"]:
        return [segment]

    prev_start = segment[0][0]
    max_delta = timedelta(seconds=0)
    cutting_point = 0

    for i, (start, end, _) in enumerate(segment):
        cur_delta = start - prev_start
        prev_start = start
        if max_delta < cur_delta:
            if min(len(segment) - i, i) >= config["words_limit"]:
                max_delta = cur_delta
                cutting_point = i

    if cutting_point == 0 or cutting_point == len(segment):
        return [segment]

    # return [segment[:cutting_point], segment[cutting_point:]]
    # 目的の長さになるまで再帰実行
    left  = split_by_pause(segment[:cutting_point], config)
    right = split_by_pause(segment[cutting_point:], config)

    return left + right


def split_by_comma(segment: Segment, config) -> list[Segment]:
    """
    最長部分列が最短になるようにカンマ位置で分割する
    """
    if len(segment) < config["words_limit"]:
        return [segment]

    seg_start = segment[0][0]
    seg_end   = segment[-1][1]
    seg_delta = seg_end - seg_start

    if seg_delta < config["duration_limit"]:
        return [segment]

    seg_middle = seg_start + (seg_delta / 2)
    max_delta = seg_delta
    cutting_point = 0
    for i, (start, end, word) in enumerate(segment):
        if word.endswith(","):
            cur_delta = abs(end - seg_middle)
            if max_delta >= cur_delta:
                max_delta = cur_delta
                cutting_point = i + 1

    if min(len(segment) - cutting_point, cutting_point) < config["words_limit"]:
        return [segment]

    # return [segment[:cutting_point], segment[cutting_point:]]
    # 目的の長さになるまで再帰実行
    left  = split_by_pause(segment[:cutting_point], config)
    right = split_by_pause(segment[cutting_point:], config)

    return left + right


def reflect_archive(lines: list[Line], config):
    print("[cyan][INFO][/]", "Reflecting archive...")

    file_path = config["archive_path"]
    archives = []
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            archives = f.read().splitlines()
    except:
        print("[yellow][WARNING][/]", f"file not found: {file_path}")
    
    print("[cyan][INFO][/]", f"{len(archives):,} lines found in archive.")

    reflected = []
    for start, end, sent in lines:
        if sent not in archives:
            reflected.append([start, end, sent])
            archives.append(sent)

    print("[cyan][INFO][/]", f"{len(reflected):,} lines left.")

    if not config["is_dry"]:
        with open(file_path, "w", encoding="utf-8") as f:
            for sent in archives:
                f.write(sent + "\n")
        print("[cyan][INFO][/]", f"archive updated: {file_path}")

    return reflected


def convert_subs_into_lines(subs_path: str, config) -> list[Line]:
    subs = []
    with open(subs_path, "r", encoding="utf-8") as f:
        subs = f.readlines()

    timed_words = convert_subs_into_words(subs)
    print("[cyan][INFO][/]", "Analyzing text...")
    nlp = load_spacy("en_core_web_sm")
    doc = nlp(" ".join(w for _, _, w in timed_words))

    if config["is_verbose"]:
        print_token_count(doc)

    segments    = convert_words_into_segments(doc, timed_words)
    print("[cyan][INFO][/]", f"{len(segments):,} sentences detected.")

    segments_by_jump = []
    for seg in segments:
        segments_by_jump += split_by_jump(seg, config)
    segments = segments_by_jump

    if config["is_verbose"]:
        print_longest_segment(segments)

    if "comma" in config["cutting"]:
        print("[cyan][INFO][/]", "Cutting by comma...")
        segments_by_comma = []
        for seg in segments:
            segments_by_comma += split_by_comma(seg, config)
        segments = segments_by_comma

        print("[cyan][INFO][/]", f"{len(segments_by_comma):,} segments generated.")

        if config["is_verbose"]:
            print_longest_segment(segments)

    if "pause" in config["cutting"]:
        print("[cyan][INFO][/]", "Cutting by pause...")
        segments_by_pause = []
        for seg in segments:
            segments_by_pause += split_by_pause(seg, config)
        segments = segments_by_pause

        print("[cyan][INFO][/]", f"{len(segments_by_pause):,} segments generated.")

        if config["is_verbose"]:
            print_longest_segment(segments)

    print("[cyan][INFO][/]", "Removing duplicates...")
    lines = []
    sentences = []
    for seg in segments:
        starts, ends, words = zip(*seg)

        seg_start = starts[0]
        seg_end   = ends[-1]
        sentence = " ".join(words)

        if sentence in sentences:
            continue

        sentences.append(sentence)
        lines.append((seg_start, seg_end, sentence))

    print("[cyan][INFO][/]", f"{len(lines):,} segments left.")

    # reflect archive
    if config["archive_path"]:
        lines = reflect_archive(lines, config)

    # add padding to the timing
    for i, (start, end, sentence) in enumerate(lines):
        if config["pad_start"] < start:
            start -= config["pad_start"]
            lines[i] = (start, end, sentence)
        if i < len(lines) - 1:
            end += config["pad_end"]
            lines[i] = (start, end, sentence)

    if config["makes_vtt"]:
        video_id = config["video_id"]
        write_in_vtt(f"{video_id}/{video_id}.out.vtt", lines)

    if config["is_verbose"]:
        nopunc = len([s for _, _, s in lines if not s.endswith((".", ",", "?", "!"))])
        print()
        print("[magenta][VERBOSE][/]", f"{nopunc} lines have no punctuation")
        
        

    return lines
