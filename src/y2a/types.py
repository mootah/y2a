from datetime import timedelta

type TimedWord = tuple[timedelta, timedelta, str]
type Line      = tuple[timedelta, timedelta, str]

type Segment   = list[TimedWord]


