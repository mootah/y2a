import os, random

from rich import print
import genanki

from y2a.entity import Segment
from y2a.utils import (
    get_note_id,
    get_media_filename
)


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


def create_notes(segments: list[Segment], config) -> list[dict]:
    video_id = config.get("video_id")
    audio_ext = config.get("audio_ext")
    image_ext = config.get("image_ext")
    notes: list[dict] = []

    for segment in segments:
        start = segment.start
        end = segment.end
        sentence = segment.sentence
        start_sec = int(start.total_seconds())
        end_sec = int(end.total_seconds())

        note_id     = get_note_id(video_id, start, end)
        translation = ""
        target      = ""
        memos       = ""
        audio_file  = get_media_filename(video_id, start, end, audio_ext)
        image_file  = get_media_filename(video_id, start, end, image_ext)
        audio_tag   = f"[sound:{audio_file}]"
        image_tag   = f"<img src=\"{image_file}\">"
        url         = f"https://www.youtube.com/watch?v={video_id}&start={start_sec}&end={end_sec}"

        notes.append({
            "id":          note_id,
            "sentence":    sentence,
            "translation": translation,
            "target":      target,
            "memos":       memos,
            "audio_file":  audio_file,
            "image_file":  image_file,
            "audio":       audio_tag,
            "image":       image_tag,
            "url":         url,
        })
        
    return notes


def write_in_apkg(notes: list[dict], media: list[str], config):
    video_id = config.get("video_id")
    front, back, style = load_templates()
    
    model = genanki.Model(
        1759125590781,
        "y2a",
        fields=[
            {"name": "id"},
            {"name": "sentence"},
            {"name": "translation"},
            {"name": "target"},
            {"name": "memos"},
            {"name": "audio"},
            {"name": "audio_file"},
            {"name": "image"},
            {"name": "url"},
        ],
        templates=[
            {
                "name": "Audio->Sentence",
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

    keys = [f["name"] for f in model.fields]
    for n in notes:
        row = [n.get(key) for key in keys]
        anki_note = genanki.Note(
            model=model,
            fields=row,
        )
        deck.add_note(anki_note)

    package = genanki.Package(deck)
    package.media_files = media

    apkg_path = f"{video_id}/{video_id}.apkg"
    package.write_to_file(apkg_path)
    
    print("[cyan][INFO][/]", f"[green]Anki package created: {apkg_path}")


def generate(segments: list[Segment], media: list[str], config) -> list[dict]:
    notes = create_notes(segments, config)

    if config.get("is_dry"):
        print("[yellow][DRY][/]", "Skipped.")
        return notes
    if not "apkg" in config.get("formats"):
        print("[cyan][INFO][/]", "Skipped.")
        return notes

    write_in_apkg(notes, media, config)
    
    return notes