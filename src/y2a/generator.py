import os, random

from rich import print
import genanki

from y2a.entity import Line
from y2a.utils import format_time


def read(file_path: str) -> str:
    text = ""
    with open(file_path, "r", encoding="utf-8") as f:
        text = f.read()
    return text


def load_templates():
    template_path = os.path.join(os.path.dirname(__file__), "template")

    front_path = os.path.join(template_path, "front.template.anki")
    back_path  = os.path.join(template_path, "back.template.anki")
    style_path = os.path.join(template_path, "style.css")

    front = read(front_path)
    back  = read(back_path)
    style = read(style_path)

    return front, back, style


def create_cards(lines: list[Line], video_id) -> list[dict]:
    cards = []
    for start, end, sentence in lines:
        start_str = format_time(start)
        end_str = format_time(end)

        note_id     = f"{video_id}_{start_str}-{end_str}"
        translation = ""
        notes       = ""
        audio_file  = f"{note_id}.mp3"
        audio       = f"[sound:{audio_file}]"
        image_tag   = f"<img src=\"{note_id}.jpg\">"
        url         = f"https://www.youtube.com/watch?v={video_id}&start={start.seconds}&end={end.seconds}"

        cards.append({
            "id":          note_id,
            "sentence":    sentence,
            "translation": translation,
            "notes":       notes,
            "audio":       audio,
            "audio_file":  audio_file,
            "image":       image_tag,
            "url":         url
        })
        
    return cards


def write_in_apkg(rows: list[list], media: list[str], video_id):
    front, back, style = load_templates()
    
    model = genanki.Model(
        1759125590781,
        "SentenceMining",
        fields=[
            {"name": "id"},
            {"name": "sentence"},
            {"name": "translation"},
            {"name": "notes"},
            {"name": "audio"},
            {"name": "audio_file"},
            {"name": "image"},
            {"name": "url"},
        ],
        templates=[
            {
                "name": "Repeating",
                "qfmt": front,
                "afmt": back,
            },
        ],
        css=style,
    )

    deck_id = random.randrange(1 << 30, 1 << 31)

    deck = genanki.Deck(
        deck_id,
        f"{video_id}"
    )

    for row in rows:
        note = genanki.Note(
            model=model,
            fields=row,
        )
        deck.add_note(note)

    package = genanki.Package(deck)
    package.media_files = media

    apkg_path = f"{video_id}/{video_id}.apkg"
    package.write_to_file(apkg_path)
    
    print("[cyan][INFO][/]", f"[green]Anki package created: {apkg_path}")


def generate(lines: list[Line], media: list[str], config) -> list[dict]:
    video_id = config.get("video_id")
    cards = create_cards(lines, video_id)

    if config.get("is_dry"):
        print("[yellow][DRY][/]", "Skipped.")
        return cards
    if not "apkg" in config.get("formats"):
        print("[cyan][INFO][/]", "Skipped.")
        return cards

    rows = [list(c.values()) for c in cards]
    write_in_apkg(rows, media, video_id)
    
    return cards