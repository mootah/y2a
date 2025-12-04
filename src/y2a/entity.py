from datetime import timedelta
from collections import UserList

def format_time(td: timedelta, delim: str = ".") -> str:
    """
    timedelta -> HH.mm.ss.mmm
    """
    total_ms = int(td.total_seconds() * 1000)
    hours, rest = divmod(total_ms, 3600 * 1000)
    minutes, rest = divmod(rest, 60 * 1000)
    seconds, millis = divmod(rest, 1000)
    return f"{hours:02}{delim}{minutes:02}{delim}{seconds:02}.{millis:03}"


class TimedWord:
    """時間情報を持つ単語を表現するクラス"""
    
    __slots__ = ("_start", "_end", "_word")
    
    def __init__(self, start: timedelta, end: timedelta, word: str) -> None:
        self._start = start
        self._end = end
        self._word = word
    
    @property
    def start(self) -> timedelta:
        return self._start
    
    @property
    def end(self) -> timedelta:
        return self._end
    
    @property
    def word(self) -> str:
        return self._word
    
    @property
    def delta(self) -> timedelta:
        return self._end - self._start
    
    def __repr__(self) -> str:
        return f"TimedWord({self._start}, {self._end}, {self._word!r})"
    
    def __eq__(self, other: object) -> bool:
        if not isinstance(other, TimedWord):
            return NotImplemented
        return (self._start == other._start and 
                self._end == other._end and 
                self._word == other._word)
    
    def __hash__(self) -> int:
        return hash((self._start, self._end, self._word))


class Segment(UserList):
    """時間情報を持つ単語のリストを表現するクラス"""
    
    def __init__(self, initlist: list[TimedWord] | None = None) -> None:
        super().__init__(initlist)
    
    def __str__(self):
        start = format_time(self.start)
        end   = format_time(self.end)
        return f"{start}-{end} \"{self.sentence}\""

    @property
    def start(self) -> timedelta:
        """先頭のTimedWordのstart"""
        if not self.data:
            raise ValueError("Segment is empty")
        return self.data[0].start
    
    @property
    def end(self) -> timedelta:
        """末尾のTimedWordのend"""
        if not self.data:
            raise ValueError("Segment is empty")
        return self.data[-1].end
    
    @property
    def sentence(self) -> str:
        """TimedWordのリストをスペースでジョイン"""
        return " ".join(item.word for item in self.data)
    
    @property
    def delta(self) -> timedelta:
        """endとstartの差"""
        if self.start > self.end:
            print(self)
            raise ValueError("something weird")
        return self.end - self.start


# 後方互換性のための型エイリアス
type Line = tuple[timedelta, timedelta, str]


