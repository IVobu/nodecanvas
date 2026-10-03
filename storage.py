import json
import os
from models import Square, Link, Folder


def export_json(squares, links, folders, background_image, filepath):
    data = {
        "version": 1,
        "background_image": background_image,
        "squares": [sq.to_dict() for sq in squares],
        "links": [ln.to_dict() for ln in links],
        "folders": [fd.to_dict() for fd in folders],
    }
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def import_json(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

    squares = [Square.from_dict(sq) for sq in data.get("squares", [])]
    links = [Link.from_dict(ln) for ln in data.get("links", [])]
    folders = [Folder.from_dict(fd) for fd in data.get("folders", [])]
    background_image = data.get("background_image", "")

    return squares, links, folders, background_image
