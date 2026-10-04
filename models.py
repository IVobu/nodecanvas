import uuid


class Square:
    def __init__(self, x, y, size=60, color="#4A90D9", name="", folder_id=None, image_path=None, locked=False, rotation=0, flip=0):
        self.id = str(uuid.uuid4())[:8]
        self.x = x
        self.y = y
        self.size = size
        self.color = color
        self.name = name
        self.folder_id = folder_id
        self.image_path = image_path
        self.locked = locked
        self.rotation = rotation
        self.flip = flip

    def contains(self, px, py):
        return self.x <= px <= self.x + self.size and self.y <= py <= self.y + self.size

    def center(self):
        return (self.x + self.size / 2, self.y + self.size / 2)

    def to_dict(self):
        return {
            "id": self.id,
            "x": self.x,
            "y": self.y,
            "size": self.size,
            "color": self.color,
            "name": self.name,
            "folder_id": self.folder_id,
            "image_path": self.image_path,
            "locked": self.locked,
            "rotation": self.rotation,
            "flip": self.flip,
        }

    @classmethod
    def from_dict(cls, data):
        sq = cls(data["x"], data["y"], data.get("size", 60), data.get("color", "#4A90D9"), data.get("name", ""), data.get("folder_id"), data.get("image_path"), data.get("locked", False), data.get("rotation", 0), data.get("flip", 0))
        sq.id = data["id"]
        return sq


class Link:
    def __init__(self, source_id, target_id, color="#888888"):
        self.id = str(uuid.uuid4())[:8]
        self.source_id = source_id
        self.target_id = target_id
        self.color = color

    def to_dict(self):
        return {
            "id": self.id,
            "source_id": self.source_id,
            "target_id": self.target_id,
            "color": self.color,
        }

    @classmethod
    def from_dict(cls, data):
        ln = cls(data["source_id"], data["target_id"], data.get("color", "#888888"))
        ln.id = data["id"]
        return ln


class Folder:
    def __init__(self, x, y, w=300, h=250, title="Dossier", collapsed=False, color="#F5F5DC"):
        self.id = str(uuid.uuid4())[:8]
        self.x = x
        self.y = y
        self.w = w
        self.h = h
        self.title = title
        self.collapsed = collapsed
        self.color = color

    def contains(self, px, py):
        return self.x <= px <= self.x + self.w and self.y <= py <= self.y + self.h

    def header_contains(self, px, py):
        header_h = 30
        return self.x <= px <= self.x + self.w and self.y <= py <= self.y + header_h

    def to_dict(self):
        return {
            "id": self.id,
            "x": self.x,
            "y": self.y,
            "w": self.w,
            "h": self.h,
            "title": self.title,
            "collapsed": self.collapsed,
            "color": self.color,
        }

    @classmethod
    def from_dict(cls, data):
        fd = cls(data["x"], data["y"], data.get("w", 300), data.get("h", 250), data.get("title", "Dossier"), data.get("collapsed", False), data.get("color", "#F5F5DC"))
        fd.id = data["id"]
        return fd
