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
- [ffmpeg](https://www.ffmpeg.org/)
- [yt-dlp](https://github.com/yt-dlp/yt-dlp)

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
  - `{VIDEO_ID}_{HH.mm.ss.mmm}-{HH.mm.ss.mmm}`
- `sentence`
  - 切り出されたセリフ
- `translation`
  - （空欄）
- `notes`
  - （空欄）
- `audio`
  - 音声 `[sound: {id}.mp3]`
- `audio_file`
  - 音声（HTML Audio 用） `{id}.mp3`
- `image`
  - スクリーンショット `<img scr="{id}.jpg">`
- `url`
  - タイムスタンプ付きの YouTube の URL

### テンプレート（Template）

- 表
  - `image`
  - `audio`
- 裏
  - `sentence`
  - `audio`
  - `translation`
  - `notes`
  - `image`
  - `url`

<img alt="front" src="https://i.gyazo.com/0a6c164d7358ffce9c89386710d7f99b.png" width="400">
<img alt="back" src="https://i.gyazo.com/ce9f9a5551d9ab114b6ba37f9b01ed1f.png" width="400">
