# Y2A: YouTube to Anki

YouTube の動画を、妥当な位置でセグメントに分割して Anki デッキにするプログラム

A program to segment YouTube videos at reasonable points and convert them into Anki decks

## 特徴（Features）

次の要件を満たした自動生成字幕がある動画にのみ対応している

- 英語
- 単語毎のタイムスタンプがある（YouTube上で一語ずつ現れる）
- 句読点がある（2025年の中旬以降に投稿された動画）

セリフの切り出しは以下の3段階で行っている

- 句読点等の表記に基づいた文の切れ目（sentence boundaries）
- 等位接続節や副詞節等の構文の切れ目（grammatical boundaries）
- タイムスタンプに基づく発話の切れ目（speech boundaries）

## 依存関係（Dependencies）

- [uv](https://github.com/astral-sh/uv)

## インストール（Installation）

```zsh
uv tool install git+https://github.com/mootah/y2a
```

## 使い方（Usage）

ヘルプ

```zsh
y2a -h
```

動画IDを指定してAnkiパッケージを生成する

```zsh
y2a video_id
```

mp4ファイルとvttファイルを直接指定する

```zsh
y2a path/to/video.mp4 -s path/to/sub.vtt
```

csv, json, txtファイルも一緒に生成する

```zsh
y2a video_id -f csv -f json -f txt -f apkg
```

整形した字幕ファイルを生成する（asbplayer等で使用するため）

```zsh
y2a video_id -f vtt --margin 0 0 --keep_dups
```

文末でのみ分割する

```zsh
y2a video_id --boundary sentence
```

セグメント前後の余白を調整する

```zsh
y2a video_id --margin 200 100
```

セグメントの長さを調節する

```zsh
y2a video_id --max_duration 5000 --min_words 3
```


## 生成されるカード（Card）

### フィールド（Field）

- `id`
  - `{VIDEO_ID}_{START}-{END}`
- `sentence`
  - 切り出されたセリフ
- `translation`
  - （空欄）
- `target`
  - （空欄）
- `memos`
  - （空欄）
- `audio`
  - 音声 `[sound: y2a-{id}.webm]`
- `audio_file`
  - 音声（HTML Audio 用） `y2a-{id}.webm`
- `image`
  - スクリーンショット `<img scr="y2a-{id}.webp">`
- `url`
  - タイムスタンプ付きの YouTube の URL

### テンプレート（Template）

- 表
  - `audio`
  - `image`
- 裏
  - `sentence`
  - `translation`
  - `audio`
  - `image`
  - `target`
  - `memos`
  - `url`
