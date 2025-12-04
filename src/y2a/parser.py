import re, html
from datetime import timedelta
from rich import print
from bs4 import BeautifulSoup

from y2a.entity import TimedWord, Segment
from y2a.utils import (
    get_spacy_document,
    print_token_count,
    print_summary
)
from y2a.splitter import (
    split_at_doc_boundaries,
    split_at_speech_boundaries,
    split_at_timestamp_boundaries
)

def parse_into_timedwords(sub_path: str) -> list[TimedWord]:
    text = ""
    with open(sub_path, "r") as f:
        text = f.read()
    soup = BeautifulSoup(text, "lxml-xml")
    
    words: list[TimedWord] = []
    max_delta = timedelta(seconds=2)

    for element in soup("text"):
        start = timedelta(milliseconds=int(element.get("t")))
        word_text = html.unescape(element.text).strip()
        end = start + max_delta
        
        if word_text.startswith("["):
            word_text = ""
        
        word_text = word_text.replace(">>", "―")
        
        word = TimedWord(start, end, word_text)
        words.append(word)

    for i, word in enumerate(words):
        if i == 0:
            continue
        if words[i-1].end > word.start:
            # TimedWordはimmutableなため、新しいインスタンスを作成
            words[i-1] = TimedWord(words[i-1].start, word.start, words[i-1].word)
    
    tokens: list[TimedWord] = []
    for word in words:
        if " " in word.word:
            for t in word.word.split(" "):
                token = TimedWord(word.start, word.end, t)
                tokens.append(token)
        else:
            tokens.append(word)
    words = tokens
    
    words = [w for w in words if w.word]

    return words

def merge_timedwords_into_segments(timedwords: list[TimedWord], sentences: list[str]) -> list[Segment]:
    words = [w.word for w in timedwords]
    segments: list[Segment] = []

    pos = 0
    for sent in sentences:
        sent_len = len(sent.split(" "))
        result = " ".join(words[pos:pos+sent_len])
        if sent != result:
            print("Text did not match")
            print(sent, words[pos:pos+sent_len])
            break
        seg = Segment(timedwords[pos:pos+sent_len])
        segments.append(seg)
        pos += sent_len
    
    # for sent in sentences:
    #     candidate = words[pos]
    #     if sent in candidate:
    #         seg = Segment(timedwords[pos:pos+1])
    #         segments.append(seg)
    #         pos += 1
    #         continue
    #     for i in range(1, words_len - pos):
    #         candidate += " " + words[pos+i]
    #         if sent in candidate:
    #             seg = Segment(timedwords[pos:pos+i+1])
    #             segments.append(seg)
    #             pos += i + 1
    #             break
    return segments


def parse(subtitle_path: str, config) -> list[Segment]:
    timedwords = parse_into_timedwords(subtitle_path)
    text = " ".join(w.word for w in timedwords)
    doc = get_spacy_document(text, config)

    if config.get("is_verbose"):
        print_token_count(doc)

    # Split doc at the sentence boundaries and grammatical boundaries
    sentences: list[str] = split_at_doc_boundaries(doc, config)

    # (timedwords, sentences) -> segments
    segments: list[Segment] = merge_timedwords_into_segments(timedwords, sentences)

    # Split at the timestamp gap
    segments = split_at_timestamp_boundaries(segments)

    # Split at the speech pause
    if "speech" in config.get("boundaries"):
        segments = split_at_speech_boundaries(segments, config)

    # Remove dups
    if not config.get("should_keep_dups"):
        print("[cyan][INFO][/]", "Removing duplicates...")
        unique_segs = []
        unique_sents = set()
        for seg in segments:
            if seg.sentence in unique_sents:
                continue
            unique_segs.append(seg)
            unique_sents.add(seg.sentence)
        segments = unique_segs
        print("[cyan][INFO][/]", f"\t-> {len(segments):,} segments.")

    # Add margins (Segmentはimmutableなため、TimedWordsを修正)
    for i, seg in enumerate(segments):
        margin_start = config.get("margin_start")
        margin_end   = config.get("margin_end")
        
        # 先頭のTimedWordを修正
        if margin_start < seg[0].start:
            first_word = seg[0]
            seg[0] = TimedWord(first_word.start - margin_start, first_word.end, first_word.word)
        
        # 末尾のTimedWordを修正
        if i < len(segments) - 1:
            last_word = seg[-1]
            seg[-1] = TimedWord(last_word.start, last_word.end + margin_end, last_word.word)

    if config.get("is_verbose"):
        print_summary(segments, config)

    return segments


