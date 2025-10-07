import os, random

from rich import print
import genanki

from .types import Line
from .utils import format_time, write_in_tsv, write_in_json


def read(file_path: str) -> str:
    text = ""
    with open(file_path, "r", encoding="utf-8") as f:
        text = f.read()
    return text


def load_template():
    template_path = os.path.join(os.path.dirname(__file__), "template")

    front_path = os.path.join(template_path, "front.html")
    back_path  = os.path.join(template_path, "back.html")
    style_path = os.path.join(template_path, "style.css")

    front = read(front_path)
    back  = read(back_path)
    style = read(style_path)

    return front, back, style


def generate_apkg(lines: list[Line], media: list[str], config):
    video_id = config["video_id"]
    rows = []
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

        rows.append([
            note_id,
            sentence,
            translation,
            notes,
            audio,
            audio_file,
            image_tag,
            url
        ])

    if config["is_dry"]:
        print("[yellow][DRY][/]", "Skipped.")

    if config["makes_tsv"]:
        write_in_tsv(f"{video_id}/{video_id}.tsv", rows)

    if config["makes_json"]:
        write_in_json(f"{video_id}/{video_id}.json", rows)

    if config["is_dry"]:
        return

    front, back, style = load_template()

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
    # templates=[
    #     {
    #         "name": "Repeating",
    #         "qfmt": "{{audio}}<br>{{image}}",
    #         "afmt": "{{FrontSide}}<hr id=answer>{{sentence}}<br>{{image}}<br><a href=\"{{url}}\">YouTube</a>",
    #     },
    # ],

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
    
    print("[cyan][INFO][/]", f"Anki package created: {apkg_path}")


