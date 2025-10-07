# Y2A: YouTube to Anki

YouTube の動画をセリフ単位で切り出して Anki デッキにするプログラム

A program that splits YouTube videos into individual dialogue segments and generates Anki flashcards

## 依存環境（Dependencies）

- (uv)[https://github.com/astral-sh/uv]
- (ffmpeg)[https://www.ffmpeg.org/]
- (yt-dlp)[https://github.com/yt-dlp/yt-dlp]

## インストール（Installation）

```zsh
uv tool install git+https://github.com/mootah/y2a
```

## 使い方（Usage）

```zsh
y2a -h
```

```zsh
y2a -i <video_id>
```

## 特徴（Features）

2025 年上旬くらい以降の、次の要件を満たした動画（自動生成字幕）にのみ対応している

- 句読点がある
- 単語毎のタイムスタンプがある

セリフの切り出しは次の手順で行っている

- spaCy を用いた文末検知
- 長過ぎる場合はカンマの位置で分割（オプション）
- 長過ぎる場合は発言の切れ目で分割（オプション）

## 生成されるカード（Card）

### フィールド

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

### テンプレート

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

## 運用方法

### 表面

以下の項目を確認する。

- 音レベルで聞き取れるか
  - 音素、音韻変化を認識できるか
  - リズム、イントネーションを認識できるか
- 意味レベルで聞き取れるか
  - 単語、表現の内容をイメージできるか
  - 聞きながらに（立ち返らずに）解釈ができるか
  - 文脈を想起できるか
- リピーティングできるか
  - 聞いた英文を脳内に保持（リテンション）できるか
  - 発言にイメージが伴っているか
  - 音素、音韻変化、リズム、イントネーションを再現できるか

必要に応じてスロー再生する。

出来にかかわらず、基本的に「Good（正解）」を押す

ただし、上記確認事項について全く歯が立たない、あるいは練習した記憶がない等の場合は、「Again（もう一度）」を押しても良い

### 裏面

リピーティングの練習をする

まずは英文を見て、自分が内容をイメージできるスピードで音読する（一語ずつゆっくりで良い）

同様のスピードで、英文を見ずに声に出す

音源を聞いて（スローからで良い）リピーティングし、発音等を確認する

オリジナルのスピードに口を慣らす

調べたことや気付きは何でもメモする

余裕があればパターンプラクティスを行う


