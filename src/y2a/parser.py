import re
from datetime import timedelta

from rich import print
from spacy.tokens.doc import Doc

from y2a.entity import TimedWord, Segment, Line
from y2a.utils import (
    get_spacy_document,
    parse_time,
    print_token_count,
    print_summary
)
from y2a.splitter import (
    split_at_doc_boundaries,
    split_at_speech_boundaries,
    split_at_timestamp_boundaries
)


def parse_subtext_into_words(subtext: list[str]) -> list[TimedWord]:
    timed_words = []
    i = 0
    while i < len(subtext):
        row = subtext[i].strip()
        if re.match(r"^\d\d:\d\d:\d\d\.\d+ -->", row):

            # time
            time_row = row
            start, end = time_row.split(" --> ")
            end = end.replace(" align:start position:0%", "")

            # word (the next next row)
            i += 2
            if i < len(subtext):
                word_row = subtext[i].strip()
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

                # word = word.replace("&gt;&gt; ", "")
                word.strip()

                if not word:
                    continue
                if word.startswith("["):
                    continue
                
                max_word_delta = timedelta(seconds=2)

                if len(word.split(" ")) > 1:
                    for w in word.split(" "):
                        timed_words.append((word_start, word_end, w))
                    continue
                elif word_end - word_start > max_word_delta:
                    word_end = word_start + max_word_delta
                timed_words.append((word_start, word_end, word))
        i += 1

    print("[cyan][INFO][/]",
          f"\t-> {len(timed_words):,} words have indivisual timestamps.")

    return timed_words


def map_timedwords_to_sentences(
    timedwords: list[TimedWord], sentences: list[str]) -> list[Segment]:

    words_list = [w for _, _, w in timedwords]
    words_len = len(words_list)
    segments: list[Segment] = []

    pos = 0
    for sent in sentences:
        candidate = words_list[pos]
        if sent in candidate:
            seg = timedwords[pos:pos+1]
            segments.append(seg)
            pos += 1
            continue
        for i in range(1, words_len - pos):
            candidate += " " + words_list[pos+i]
            if sent in candidate:
                seg = timedwords[pos:pos+i+1]
                segments.append(seg)
                pos += i + 1
                break

    return segments


def merge_segments_into_lines(segments: list[Segment]) -> list[Line]:
    lines: list[Line] = []
    for seg in segments:
        starts, ends, words = zip(*seg)
        seg_start = starts[0]
        seg_end   = ends[-1]
        sentence = " ".join(words)
        lines.append((seg_start, seg_end, sentence))
    return lines


def parse(subtitle_path: str, config) -> list[Line]:
    subtext: list[str] = []

    with open(subtitle_path, "r", encoding="utf-8") as f:
        subtext = f.readlines()

    timedwords = parse_subtext_into_words(subtext)

    text = " ".join(w for _, _, w in timedwords)
    doc = get_spacy_document(text, config)

    if config.get("is_verbose"):
        print_token_count(doc)

    # Split doc at the sentence boundaries and grammatical boundaries
    sentences: list[str] = split_at_doc_boundaries(doc, config)

    # (timedwords, sentences) -> segments
    segments: list[Segment] = map_timedwords_to_sentences(timedwords, sentences)

    # Split at the timestamp gap
    segments = split_at_timestamp_boundaries(segments)

    # Split at the speech pause
    if "speech" in config.get("boundaries"):
        segments = split_at_speech_boundaries(segments, config)

    # Merge segments into lines
    lines: list[Line] = merge_segments_into_lines(segments)

    # Remove dups
    if not config.get("should_keep_dups"):
        print("[cyan][INFO][/]", "Removing duplicates...")
        unique_lines = []
        unique_sents = set()
        for start, end, sentence in lines:
            if sentence in unique_sents:
                continue
            unique_lines.append((start, end, sentence))
            unique_sents.add(sentence)
        lines = unique_lines
        print("[cyan][INFO][/]", f"\t-> {len(lines):,} segments.")

    # Add margins
    for i, (start, end, sentence) in enumerate(lines):
        margin_start = config.get("margin_start")
        margin_end   = config.get("margin_end")
        if margin_start < start:
            start -= margin_start
            lines[i] = (start, end, sentence)
        if i < len(lines) - 1:
            end += margin_end
            lines[i] = (start, end, sentence)

    if config.get("is_verbose"):
        print_summary(lines, config)

    return lines


