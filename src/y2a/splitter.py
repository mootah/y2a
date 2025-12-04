import re
from datetime import timedelta
from spacy.tokens import Token
from spacy.tokens.doc import Doc
from rich import print
from y2a.entity import Segment

# 副詞節を導く従属接続詞（分割対象）
SUBORDINATORS = {
    "because", "cuz", "coz", "although",
    "if", "unless",
    "when", "while", "before", "after", "since", "until", "till",
}

def is_nominal_clause_marker(token: Token):
    norm = token.text.lower()
    if norm not in {"that", "if", "whether"}:
        return False

    # 従属接続詞でない場合は除外（関係副詞などを区別）
    if token.dep_ != "mark":
        return False

    head = token.head

    # 名詞節の条件：節が動詞の補語になっている
    if head.dep_ in {"ccomp", "xcomp", "obj"}:
        return True

    # 動詞に直接ぶら下がり、副詞節ではなく補語の場合
    if head.pos_ == "VERB" and head.dep_ not in {"advcl"}:
        return True

    return False


def is_clause_level_cc(token: Token):
    """等位接続詞（and, but, or）が節レベルかどうか判定"""
    if token.dep_ != "cc":
        return False
    
    # 判定方法: 等位接続詞の直後が節（動詞を含む）かどうかで判定する
    # 例: "I went home and I slept." -> and の後に I(動詞主語が続く) -> 節レベル
    # 例: "cats and dogs" -> and の後に dogs(名詞) -> 句レベル
    try:
        head = token.head

        if head.pos_ == "VERB" and head.dep_ == "ROOT":
            return True

        # head の conjunct を探す（head の依存構造で conj でマークされた要素）
        for child in head.children:
            if child.dep_ == "conj":
                # conj の要素が動詞なら、この and は節レベル
                if child.pos_ == "VERB":
                    return True
    except Exception:
        pass

    return False  # 句レベル（cats and dogs 等）


def get_sentence_boundaries(doc: Doc) -> set:
    split_points = set()
    
    # 通常のsentence boundary
    for sent in doc.sents:
        if sent.end < len(doc):
            split_points.add(sent.end - 1)
    
    # ダブルクオーテーションペアの処理
    quote_indices = [i for i, t in enumerate(doc) if t.text == '"']
    
    # ペアで処理（奇数番目=開始、偶数番目=終了）
    for i in range(0, len(quote_indices) - 1, 2):
        opening_idx = quote_indices[i]
        closing_idx = quote_indices[i + 1]
        
        # 開始クオーテーション直前で分割
        if opening_idx > 0:
            split_points.add(opening_idx - 1)
        
        # 終了クオーテーション直後で分割
        if closing_idx < len(doc) - 1:
            split_points.add(closing_idx)

    return split_points


def get_grammatical_boundaries(doc: Doc) -> set:
    split_points = set()
    
    for i, t in enumerate(doc):
        candidate = False

        if is_nominal_clause_marker(t): # 名詞節（補文）
            candidate = False
        elif t.dep_ == "mark": # 副詞節導入語 ( because 等)
            lower = t.text.lower()
            lower = re.sub(r'[^a-zA-Z]', '', lower)
            # if lower in SUBORDINATORS:
            if lower not in {"as", "that", "though"}:
                # 通常は mark の直前で分割（ただし同一文内に限る）
                try:
                    sent = t.sent
                    if t.i > sent.start:
                        split_idx = t.i - 1
                        candidate = True
                    else:
                        # mark が文頭にある場合: "If I go there, I can..."
                        # 同一文内のカンマを探してその位置で分割する
                        comma_idx = None
                        for tok in sent:
                            if tok.text == ",":
                                comma_idx = tok.i
                                break
                        if comma_idx is not None:
                            split_idx = comma_idx
                            candidate = True
                        else:
                            candidate = False
                except Exception:
                    candidate = False
        # 等位接続詞（節レベル）
        elif t.dep_ == "cc" and is_clause_level_cc(t):
            split_idx = i - 1 if i - 1 >= 0 else i
            candidate = True
        # カンマ
        elif t.text == ",":
            split_idx = i
            candidate = True

        if candidate:
            split_points.add(split_idx)

    return split_points


def split_at_doc_boundaries(doc: Doc, config) -> list[str]:
    min_words = config.get("min_words")
    
    if "sentence" in config.get("boundaries"):
        print("[cyan][INFO][/]", "Splitting at the sentence boundaries ...")
        sentence_boundaries = get_sentence_boundaries(doc)
        print("[cyan][INFO][/]", f"\t-> {len(sentence_boundaries) + 1:,} segments.")
    else:
        sentence_boundaries = set()
        
    if "grammar" in config.get("boundaries"):
        print("[cyan][INFO][/]", "Splitting at the grammatical boundaries ...")
        grammatical_boundaries = get_grammatical_boundaries(doc)
    else:
        grammatical_boundaries = set()
    
    split_points = sorted(sentence_boundaries | grammatical_boundaries)

    segments = []
    last = 0

    for i, idx in enumerate(split_points):
        seg_tokens = doc[last:idx+1]
        
        if i + 1 < len(split_points):
            next_tokens = doc[idx+1:split_points[i+1]+1]
        else:
            next_tokens = doc[idx+1:]

        is_sentence_boundary = idx in sentence_boundaries
        
        if is_sentence_boundary:
            # 文末境界: 最小語数チェックなしで分割
            segments.append(seg_tokens.text)
            last = idx + 1
        else:
            # 文法的分割: 現在のセグメントと次のセグメント両方の最小語数をチェック
            if len(seg_tokens) >= min_words and len(next_tokens) >= min_words:
                segments.append(seg_tokens.text)
                last = idx + 1
    
    # 最後の部分を追加
    if last < len(doc):
        segments.append(doc[last:].text)
    
    if "grammar" in config.get("boundaries"):
        print("[cyan][INFO][/]", f"\t-> {len(segments) + 1:,} segments.")

    return segments


def split_at_speech_boundaries(segments: list[Segment], config) -> list[Segment]:
    print("[cyan][INFO][/]", "Splitting at the speech boundareis ...")

    min_words = config.get("min_words")
    max_duration= config.get("max_duration")

    def _split(segment: Segment) -> list[Segment]:
        """
        単語の時間が最も長い箇所で分割する
        """

        if len(segment) < min_words:
            return [segment]

        seg_start = segment.start
        seg_end   = segment.end
        seg_delta = seg_end - seg_start

        if seg_delta < max_duration:
            return [segment]

        prev_start = segment[0].start
        max_delta = timedelta(seconds=0)
        cutting_point = 0

        for i, word in enumerate(segment):
            cur_delta = word.start - prev_start
            prev_start = word.start
            if max_delta < cur_delta:
                if min(len(segment) - i, i) >= min_words:
                    max_delta = cur_delta
                    cutting_point = i

        if cutting_point == 0 or cutting_point == len(segment):
            return [segment]

        # 目的の長さになるまで再帰実行
        left  = _split(Segment(segment[:cutting_point]))
        right = _split(Segment(segment[cutting_point:]))

        return left + right

    results: list[Segment] = []
    for seg in segments:
        results += _split(seg)
    
    print("[cyan][INFO][/]", f"\t-> {len(results):,} segments.")

    return results
    

def split_at_timestamp_boundaries(segments: list[Segment]) -> list[Segment]:
    print("[cyan][INFO][/]", "Splitting at the timestamp gaps...")

    def _split(segment: Segment) -> list[Segment]:
        new_segments = []
        current_seg = []
        length = len(segment)

        for i, word in enumerate(segment):
            current_seg.append(word)
            if i + 1 >= length:
                continue
            next_word = segment[i + 1]
            if next_word.start - word.end >= timedelta(seconds=1):
                new_segments.append(Segment(current_seg))
                current_seg = []
        if current_seg:
            new_segments.append(Segment(current_seg))

        return new_segments

    results = []
    for seg in segments:
        results += _split(seg)

    print("[cyan][INFO][/]", f"\t-> {len(results):,} segments.")

    return results

