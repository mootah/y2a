import re
from datetime import timedelta
from spacy.tokens import Token
from spacy.tokens.doc import Doc
from rich.progress import track
from .entity import Segment

# 副詞節を導く従属接続詞（分割対象）
SUBORDINATORS = {
    "because", "cuz", "coz", "although",
    # "though", "even", "even though", "even if",
    "if", "unless",
    "when", "while", "before", "after", "since", "until", "till",
    # "as soon as", "so that", "in order that"
}

END_PUNCT = {".", "?", "!"}

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


def get_split_indices(doc: Doc, config) -> set:
    """
    文書 `doc` から分割位置のインデックスを返す。
    - 終端句読点はその位置で分割
    - `mark`（because 等）と節レベルの `cc` は前のトークンで分割
    - カンマはその位置で分割
    - 重複や逆順にならないよう昇順で返す
    """
    split_points = set()
    for i, t in enumerate(doc):
        candidate = False
        # 終端句読点
        if t.text in END_PUNCT:
            split_idx = i
            candidate = True
        # mark（副詞節導入語）: because 等（英字のみで判定）
        elif t.dep_ == "mark":
            lower = t.text.lower()
            lower = re.sub(r'[^a-zA-Z]', '', lower)
            if lower in SUBORDINATORS:
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


def split_by_semantics(doc: Doc, config):
    min_words = config["words_limit"]
    
    split_points = list(get_split_indices(doc, config))
    split_points.sort()

    segments = []
    last = 0

    for i, idx in enumerate(split_points):
        # 文節候補（idx はセグメントの最後のトークンの index）
        cur_token = doc[idx]
        seg_tokens = doc[last:idx+1]
        
        if i + 1 < len(split_points):
            next_tokens = doc[idx+1:split_points[i+1]+1]
        else:
            next_tokens = doc[idx+1:]

        # 文末パンクチュエーション（ピリオド等）は従来通りその位置で分割
        if cur_token.text in END_PUNCT:
            segments.append(seg_tokens.text)
            last = idx + 1
            continue

        # 最小語数チェック（現在の seg と次の seg 両方）
        if len(seg_tokens) >= min_words and len(next_tokens) >= min_words:
            segments.append(seg_tokens.text)
            last = idx + 1
    
    # 最後の部分を追加
    if last < len(doc):
        segments.append(doc[last:].text)

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