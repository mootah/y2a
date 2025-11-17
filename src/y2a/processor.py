import re
from datetime import timedelta

from rich import print
from rich.progress import track
from spacy.tokens.doc import Doc

from .entity import TimedWord, Segment, Line
from .utils import (
    get_spacy_document,
    parse_time,
    format_time,
    write_in_txt,
    write_in_vtt,
    print_longest_segment,
    print_token_count,
)
from .splitter import (
    split_by_semantics,
    split_by_jump,
    split_by_pause
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


def convert_words_into_segments(doc: Doc, timed_words: list[TimedWord], config) -> list[Segment]:
    """
    Convert timed_words and sentences from doc into segments.
    Handles cases where words span multiple tokens (e.g., "one of").
    For each sentence, find the minimal timed_words subsequence that covers it.
    """
    # timed_words_list = list(timed_words)
    words_list = [w for _, _, w in timed_words]
    words_len = len(words_list)
    sentences = split_by_semantics(doc, config)

    segments = []
    pos = 0  # Current position in timed_words_list

    for sent in track(sentences, description="Splitting"):
        sent_text = sent.strip()
        
        # Find the minimal range of timed_words that covers this sentence
        # by concatenating words until we match or exceed the sentence text
        best_cnt = 0
        for i in range(1, words_len - pos + 1):
            # Concatenate words[pos:pos+i] with spaces
            candidate_text = " ".join(words_list[pos:pos+i])
            
            # Check if sent_text is a substring of candidate_text (or vice versa check containment)
            # We want the minimal i such that sent_text is covered
            if sent_text in candidate_text or candidate_text.strip().startswith(sent_text):
                best_cnt = i
                # Check if we've captured at least the full sentence
                if sent_text in candidate_text:
                    break

        # If we found a match, use those words
        if best_cnt > 0:
            seg = list(timed_words[pos:pos + best_cnt])
            if len(seg):
                segments.append(seg)
            pos += best_cnt
        else:
            # Fallback: move forward by 1 to avoid infinite loop
            pos += 1

    return segments


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

    if not config["no_archive_update"]:
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

    text = " ".join(w for _, _, w in timed_words)
    doc = get_spacy_document(text, config)

    if config["is_verbose"]:
        print_token_count(doc)

    segments    = convert_words_into_segments(doc, timed_words, config)
    print("[cyan][INFO][/]", f"{len(segments):,} sentences detected.")

    segments_by_jump = []
    for seg in segments:
        segments_by_jump += split_by_jump(seg, config)
    segments = segments_by_jump

    if config["is_verbose"]:
        print_longest_segment(segments)

    # if "comma" in config["cutting"]:
    #     print("[cyan][INFO][/]", "Cutting by comma...")
    #     segments_by_comma = []
    #     for seg in segments:
    #         segments_by_comma += split_by_comma(seg, config)
    #     segments = segments_by_comma
    #
    #     print("[cyan][INFO][/]", f"{len(segments_by_comma):,} segments generated.")
    #
    #     if config["is_verbose"]:
    #         print_longest_segment(segments)

    if "pause" in config["cutting"]:
        print("[cyan][INFO][/]", "Cutting by pause...")
        segments_by_pause = []
        for seg in segments:
            segments_by_pause += split_by_pause(seg, config)
        segments = segments_by_pause

        print("[cyan][INFO][/]", f"{len(segments_by_pause):,} segments generated.")

        if config["is_verbose"]:
            print_longest_segment(segments)
    
    # merge each segment into a sentence
    lines = []
    for seg in segments:
        starts, ends, words = zip(*seg)
        seg_start = starts[0]
        seg_end   = ends[-1]
        sentence = " ".join(words)
        lines.append((seg_start, seg_end, sentence))

    # remove dups
    if not config["keeps_dups"]:
        print("[cyan][INFO][/]", "Removing duplicates...")
        unique_lines = []
        unique_sents = set()
        for start, end, sentence in lines:
            if sentence in unique_sents:
                continue
            unique_lines.append((start, end, sentence))
            unique_sents.add(sentence)
        lines = unique_lines
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

    if config["makes_txt"]:
        video_id = config["video_id"]
        write_in_txt(f"{video_id}/{video_id}.out.txt", lines)

    if config["is_verbose"]:
        duras = [e - s for s, e, _ in lines]
        
        max_sec = int(config["duration_limit"].total_seconds())
        dura_counts = [0 for _ in range(max_sec)]
        over_max_sec = 0
        
        for d in duras:
            found = False
            for i in range(len(dura_counts)):
                if d <= timedelta(seconds=i+1):
                    dura_counts[i] += 1
                    found = True
                    break
            if not found:
                over_max_sec += 1

        print()
        for i, d in enumerate(dura_counts):
            print("[magenta][VERBOSE][/]", f"~ {i+1} sec: {d:,} lines")
        print("[magenta][VERBOSE][/]", f"{max_sec} sec ~: {over_max_sec:,} lines")

        total = sum(duras, timedelta())
        print()
        print("[magenta][VERBOSE][/]", f"{format_time(total, delim=':')} in total")

    if config["is_verbose"]:
        nopunc = len([s for _, _, s in lines if not s.endswith((".", ",", "?", "!"))])
        print()
        print("[magenta][VERBOSE][/]", f"{nopunc} lines have no punctuation")

    return lines


