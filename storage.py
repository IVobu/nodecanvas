import json
from models import Square, Link, Folder

DEFAULT_BACKGROUND = {"image": "", "x": 0, "y": 0, "width": 0, "height": 0, "locked": False, "rotation": 0}


def _normalize_background(background):
    if isinstance(background, dict):
        normalized = dict(DEFAULT_BACKGROUND)
        for key in DEFAULT_BACKGROUND:
            if key in background:
                normalized[key] = background[key]
        return normalized
    if isinstance(background, str) and background:
        return {"image": background, "x": 0, "y": 0, "width": 0, "height": 0, "locked": False}
    return dict(DEFAULT_BACKGROUND)


def export_json(squares, links, folders, background, filepath, settings=None):
    background = _normalize_background(background)
    data = {
        "version": 1,
        "background": background,
        "background_image": background["image"],
        "squares": [sq.to_dict() for sq in squares],
        "links": [ln.to_dict() for ln in links],
        "folders": [fd.to_dict() for fd in folders],
        "settings": settings or {"link_color": "#888888", "square_size": 60, "link_width": 3},
    }
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def import_json(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

    squares = [Square.from_dict(sq) for sq in data.get("squares", [])]
    links = [Link.from_dict(ln) for ln in data.get("links", [])]
    folders = [Folder.from_dict(fd) for fd in data.get("folders", [])]

    raw = data["background"] if "background" in data else data.get("background_image", "")
    background = _normalize_background(raw)

    settings = data.get("settings", {"link_color": "#888888", "square_size": 60, "link_width": 3})

    return squares, links, folders, background, settings
