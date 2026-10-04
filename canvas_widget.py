"""Canvas Tkinter de NodeCanvas.

Principes de cette version :
- chaque objet (carré, dossier) est dessiné UNE fois ; on le déplace avec
  Canvas.move() au lieu de tout supprimer / redessiner à chaque événement ;
- le survol ne redessine que les liens ;
- toutes les coordonnées passent par canvasx/canvasy (le panoramique marche) ;
- les tags canvas sont préfixés (un id hexadécimal 100 % numérique serait
  sinon interprété par Tk comme un numéro d'item).
"""
import os
import uuid
import tkinter as tk

from models import Square, Link, Folder

try:
    from PIL import Image, ImageTk, ImageGrab
    PIL_AVAILABLE = True
except ImportError:  # l'appli reste utilisable sans images
    Image = ImageTk = ImageGrab = None
    PIL_AVAILABLE = False

try:
    from tkinterdnd2 import DND_FILES
    TKDND_AVAILABLE = True
except ImportError:
    DND_FILES = None
    TKDND_AVAILABLE = False

IMAGE_EXT = (".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp")
ASSETS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")
MAX_BG_SIDE = 4096      # on borne la taille mémoire de l'image de fond
MAX_IMG_SIDE = 1024     # idem pour les images dans les carrés
HANDLE = 12             # taille des poignées de redimensionnement
HEADER_H = 30           # hauteur de l'en-tête d'un dossier
SELECT_COLOR = "#4FC3F7"
LOCK_COLOR = "#FFD700"


class NodeCanvas(tk.Canvas):
    def __init__(self, parent, **kwargs):
        super().__init__(parent, bg="#2D2D2D", highlightthickness=0, **kwargs)

        # --- données (attributs conservés pour storage.py / main.py) ---
        self.squares = []
        self.links = []
        self.folders = []
        self.square_size = 60

        self.background_image = None
        self.bg_original = None
        self.bg_photo = None
        self.bg_x = 0
        self.bg_y = 0
        self.bg_width = 0
        self.bg_height = 0

        # --- état d'interaction ---
        self.selected_square = None
        self.selected_folder = None
        self.hovered_square = None
        self.connecting_from = None
        self.connect_line = None
        self.context_menu_x = 200
        self.context_menu_y = 200
        self._mode = None        # move | resize | folder | bg_move | bg_resize | connect
        self._last = (0, 0)
        self._anchor = (0, 0)
        self._orig = None

        # --- caches d'images ---
        self._images = {}        # id carré -> image PIL (ou None si échec)
        self._photo_cache = {}   # id carré -> (clé, PhotoImage)

        self._build_context_menu()
        self._bind_events()
        self._setup_dnd()

    # ------------------------------------------------------------------
    # Initialisation
    # ------------------------------------------------------------------
    def _build_context_menu(self):
        m = tk.Menu(self, tearoff=0)
        self.context_menu = m
        m.add_command(label="Nouveau carré", command=self._add_square_at_cursor)
        m.add_command(label="Nouveau dossier", command=self._add_folder_at_cursor)
        m.add_separator()
        m.add_command(label="Changer couleur", command=self._change_color)
        m.add_command(label="Renommer", command=self._rename)
        m.add_separator()
        m.add_command(label="Coller image (Ctrl+V)", command=self._paste_from_clipboard)
        m.add_separator()
        m.add_command(label="Verrouiller/Déverrouiller", command=self._toggle_lock)
        m.add_separator()
        m.add_command(label="Supprimer", command=self._delete_selected)

    def _bind_events(self):
        self.bind("<Button-1>", self._on_left_click)
        self.bind("<B1-Motion>", self._on_drag)
        self.bind("<ButtonRelease-1>", self._on_release)
        self.bind("<Double-Button-1>", self._on_double_click)
        self.bind("<Button-3>", self._on_right_click)
        self.bind("<Button-2>", lambda e: self.scan_mark(e.x, e.y))
        self.bind("<B2-Motion>", lambda e: self.scan_dragto(e.x, e.y, gain=1))
        self.bind("<Motion>", self._on_motion)
        self.bind("<Leave>", self._on_leave)
        self.bind("<Control-v>", lambda e: self._paste_from_clipboard())
        self.bind("<Delete>", lambda e: self._delete_selected())

    def _setup_dnd(self):
        # nécessite que la fenêtre racine soit un TkinterDnD.Tk()
        if TKDND_AVAILABLE and hasattr(self, "drop_target_register"):
            self.drop_target_register(DND_FILES)
            self.dnd_bind("<<Drop>>", self._on_drop)
            self.dnd_bind("<<DropEnter>>", lambda e: self.config(highlightbackground="#FFD700", highlightthickness=2))
            self.dnd_bind("<<DropLeave>>", lambda e: self.config(highlightthickness=0))

    # ------------------------------------------------------------------
    # Utilitaires
    # ------------------------------------------------------------------
    def _pos(self, event):
        """Coordonnées canvas (tient compte du panoramique)."""
        return self.canvasx(event.x), self.canvasy(event.y)

    @staticmethod
    def _tag(obj):
        prefix = "sq_" if isinstance(obj, Square) else "fd_"
        return prefix + obj.id

    @staticmethod
    def _in_handle(x, y, rx, ry):
        return rx - HANDLE <= x <= rx and ry - HANDLE <= y <= ry

    def _folder_by_id(self, fd_id):
        for fd in self.folders:
            if fd.id == fd_id:
                return fd
        return None

    def _members(self, fd):
        return [s for s in self.squares if s.folder_id == fd.id]

    def _visible(self, sq):
        if not sq.folder_id:
            return True
        fd = self._folder_by_id(sq.folder_id)
        return not (fd and fd.collapsed)

    def _find_square(self, sq_id):
        for sq in self.squares:
            if sq.id == sq_id:
                return sq
        return None

    def _square_at(self, x, y):
        for sq in reversed(self.squares):
            if self._visible(sq) and sq.contains(x, y):
                return sq
        return None

    def _folder_at(self, x, y):
        for fd in reversed(self.folders):
            h = HEADER_H if fd.collapsed else fd.h
            if fd.x <= x <= fd.x + fd.w and fd.y <= y <= fd.y + h:
                return fd
        return None

    def _restack(self):
        """Ordre : fond < dossiers < liens < carrés."""
        self.tag_lower("folder")
        self.tag_lower("background")

    # ------------------------------------------------------------------
    # API publique
    # ------------------------------------------------------------------
    def add_square(self, x, y, size=None, color="#4A90D9", name=""):
        sq = Square(x, y, size or self.square_size, color, name)
        self.squares.append(sq)
        self._draw_square(sq)
        return sq

    def add_folder(self, x, y, w=300, h=250, title="Dossier"):
        fd = Folder(x, y, w, h, title)
        self.folders.append(fd)
        self._draw_folder(fd)
        return fd

    def add_link(self, source_id, target_id):
        for ln in self.links:
            if ln.source_id == source_id and ln.target_id == target_id:
                return None
        ln = Link(source_id, target_id)
        self.links.append(ln)
        return ln

    def load_data(self, squares, links, folders, background_image):
        self.squares = squares
        self.links = links
        self.folders = folders
        self._images.clear()
        self._photo_cache.clear()
        self.selected_square = self.selected_folder = self.hovered_square = None
        self.set_background_image(background_image)
        self._redraw()

    # ------------------------------------------------------------------
    # Dessin
    # ------------------------------------------------------------------
    def _redraw(self):
        """Redessin complet : seulement au chargement / changement global."""
        self.delete("all")
        self.connect_line = None
        self._redraw_background()
        for fd in self.folders:
            self._draw_folder(fd)
        for sq in self.squares:
            self._draw_square(sq)
        self._update_links()
        self._restack()

    def _draw_square(self, sq, fast=False):
        tag = self._tag(sq)
        self.delete(tag)
        if not self._visible(sq):
            return
        x2, y2 = sq.x + sq.size, sq.y + sq.size
        if sq is self.selected_square:
            outline, width = SELECT_COLOR, 3
        elif sq.locked:
            outline, width = LOCK_COLOR, 3
        else:
            outline, width = "#FFFFFF", 2
        tags = ("square", tag)
        self.create_rectangle(sq.x, sq.y, x2, y2, fill=sq.color, outline=outline, width=width, tags=tags)
        cx, cy = sq.center()
        photo = self._photo_for(sq, fast)
        if photo:
            self.create_image(cx, cy, image=photo, tags=tags)
            self.create_text(cx, y2 - 10, text=sq.name[:12], fill="#FFFFFF", font=("Segoe UI", 7), tags=tags)
        else:
            self.create_text(cx, cy, text=sq.name, fill="#FFFFFF", font=("Segoe UI", 9, "bold"),
                             width=max(sq.size - 6, 10), tags=tags)
        if not sq.locked:
            self.create_rectangle(x2 - HANDLE, y2 - HANDLE, x2, y2, fill=LOCK_COLOR, outline="#FFFFFF", width=1, tags=tags)

    def _draw_folder(self, fd):
        tag = self._tag(fd)
        self.delete(tag)
        tags = ("folder", tag)
        outline = SELECT_COLOR if fd is self.selected_folder else "#AAAAAA"
        width = 3 if fd is self.selected_folder else 1
        if fd.collapsed:
            self.create_rectangle(fd.x, fd.y, fd.x + fd.w, fd.y + HEADER_H, fill=fd.color, outline=outline, width=width, tags=tags)
            sign = "+"
        else:
            self.create_rectangle(fd.x, fd.y, fd.x + fd.w, fd.y + fd.h, fill=fd.color, outline=outline, width=width, tags=tags)
            self.create_rectangle(fd.x, fd.y, fd.x + fd.w, fd.y + HEADER_H, fill="#E8E8E8", outline="#AAAAAA", width=1, tags=tags)
            sign = "-"
        self.create_text(fd.x + 10, fd.y + HEADER_H / 2, text=f"{sign} {fd.title}", fill="#333333",
                         anchor="w", font=("Segoe UI", 10, "bold"), tags=tags)
        self.tag_lower(tag)
        self.tag_lower("background")

    def _update_links(self):
        """Redessine uniquement les liens du carré survolé (peu coûteux)."""
        self.delete("link")
        h = self.hovered_square
        if h is None or not self._visible(h):
            return
        for ln in self.links:
            if h.id not in (ln.source_id, ln.target_id):
                continue
            src, tgt = self._find_square(ln.source_id), self._find_square(ln.target_id)
            if not src or not tgt or not self._visible(src) or not self._visible(tgt):
                continue
            x1, y1 = src.center()
            x2, y2 = tgt.center()
            self.create_line(x1, y1, x2, y2, fill=ln.color, width=3, tags="link")
        try:
            self.tag_lower("link", "square")
        except tk.TclError:
            pass

    # ------------------------------------------------------------------
    # Images (carrés)
    # ------------------------------------------------------------------
    @staticmethod
    def _resolve(path):
        return path if os.path.isabs(path) else os.path.join(os.path.dirname(ASSETS_DIR), path)

    def _load_image(self, path):
        if not PIL_AVAILABLE or not path:
            return None
        try:
            img = Image.open(self._resolve(path))
            img.load()
            img.thumbnail((MAX_IMG_SIDE, MAX_IMG_SIDE))
            return img
        except Exception:
            return None

    def _photo_for(self, sq, fast=False):
        if not sq.image_path or not PIL_AVAILABLE:
            return None
        if sq.id not in self._images:
            self._images[sq.id] = self._load_image(sq.image_path)
        img = self._images[sq.id]
        if img is None:
            return None
        key = (sq.size, fast)
        cached = self._photo_cache.get(sq.id)
        if cached and cached[0] == key:
            return cached[1]
        box = max(sq.size - 4, 1)
        scale = min(box / img.width, box / img.height)
        size = (max(int(img.width * scale), 1), max(int(img.height * scale), 1))
        resample = Image.NEAREST if fast else Image.LANCZOS
        photo = ImageTk.PhotoImage(img.resize(size, resample))
        self._photo_cache[sq.id] = (key, photo)
        return photo

    def _add_image_square(self, filepath, x, y, size=300):
        img = self._load_image(filepath)
        if img is None:
            return None
        sq = Square(x - size / 2, y - size / 2, size, "#3A3A3A",
                    os.path.basename(filepath), image_path=filepath)
        self._images[sq.id] = img
        self.squares.append(sq)
        self._draw_square(sq)
        return sq

    def _paste_from_clipboard(self):
        if not PIL_AVAILABLE:
            return
        try:
            data = ImageGrab.grabclipboard()
        except Exception:
            return
        if data is None:
            return
        cx = self.canvasx(self.winfo_width() / 2)
        cy = self.canvasy(self.winfo_height() / 2)
        if isinstance(data, list):  # fichiers copiés depuis l'explorateur
            for i, f in enumerate(p for p in data if str(p).lower().endswith(IMAGE_EXT)):
                self._add_image_square(str(f), cx + 20 * i, cy + 20 * i)
            return
        # image brute : on la sauvegarde pour qu'elle survive à l'export JSON
        try:
            os.makedirs(ASSETS_DIR, exist_ok=True)
            path = os.path.join(ASSETS_DIR, f"paste_{uuid.uuid4().hex[:8]}.png")
            data.save(path)
        except Exception:
            return
        self._add_image_square(path, cx, cy)

    def _on_drop(self, event):
        self.config(highlightthickness=0)
        x = self.canvasx(event.x_root - self.winfo_rootx())
        y = self.canvasy(event.y_root - self.winfo_rooty())
        files = [f for f in self.tk.splitlist(event.data) if f.lower().endswith(IMAGE_EXT)]
        for i, f in enumerate(files):
            self._add_image_square(f, x + 20 * i, y + 20 * i)

    # ------------------------------------------------------------------
    # Image de fond
    # ------------------------------------------------------------------
    def set_background_image(self, filepath):
        self.delete("background")
        self.background_image = None
        self.bg_original = None
        self.bg_photo = None
        self.bg_x = self.bg_y = 0
        self.bg_width = self.bg_height = 0
        if not filepath or not PIL_AVAILABLE:
            return
        try:
            img = Image.open(filepath)
            img.load()
            if max(img.size) > MAX_BG_SIDE:
                img.thumbnail((MAX_BG_SIDE, MAX_BG_SIDE))
        except Exception:
            return
        self.bg_original = img
        self.bg_width, self.bg_height = img.size
        self.background_image = filepath
        self._redraw_background()

    def _redraw_background(self, fast=False):
        self.delete("background")
        if self.bg_original is None:
            return
        size = (max(int(self.bg_width), 1), max(int(self.bg_height), 1))
        img = self.bg_original
        if size != img.size:
            img = img.resize(size, Image.NEAREST if fast else Image.LANCZOS)
        self.bg_photo = ImageTk.PhotoImage(img)
        self.create_image(self.bg_x, self.bg_y, image=self.bg_photo, anchor="nw", tags="background")
        self.tag_lower("background")

    def _bg_hit(self, x, y):
        return (self.bg_original is not None
                and self.bg_x <= x <= self.bg_x + self.bg_width
                and self.bg_y <= y <= self.bg_y + self.bg_height)

    # ------------------------------------------------------------------
    # Sélection
    # ------------------------------------------------------------------
    def _select(self, sq=None, fd=None):
        old_sq, old_fd = self.selected_square, self.selected_folder
        self.selected_square, self.selected_folder = sq, fd
        if old_sq is not None and old_sq is not sq:
            self._draw_square(old_sq)
        if old_fd is not None and old_fd is not fd:
            self._draw_folder(old_fd)
        if sq is not None and sq is not old_sq:
            self._draw_square(sq)
        if fd is not None and fd is not old_fd:
            self._draw_folder(fd)
        self._update_links()

    # ------------------------------------------------------------------
    # Événements souris
    # ------------------------------------------------------------------
    def _on_left_click(self, event):
        self.focus_set()
        x, y = self._pos(event)
        self._mode = None

        sq = self._square_at(x, y)          # les carrés passent AVANT le fond
        if sq:
            self._select(sq=sq)
            if not sq.locked:
                if self._in_handle(x, y, sq.x + sq.size, sq.y + sq.size):
                    self._mode, self._anchor, self._orig = "resize", (x, y), sq.size
                else:
                    self._mode, self._last = "move", (x, y)
            return

        fd = self._folder_at(x, y)
        if fd:
            self._select(fd=fd)
            if fd.header_contains(x, y):
                self._mode, self._last = "folder", (x, y)
            return

        self._select()
        if self._bg_hit(x, y):
            if self._in_handle(x, y, self.bg_x + self.bg_width, self.bg_y + self.bg_height):
                self._mode, self._anchor = "bg_resize", (x, y)
                self._orig = (self.bg_width, self.bg_height)
            else:
                self._mode, self._last = "bg_move", (x, y)

    def _on_drag(self, event):
        x, y = self._pos(event)
        mode = self._mode
        if mode is None:
            return
        dx, dy = x - self._last[0], y - self._last[1]

        if mode == "move":
            sq = self.selected_square
            sq.x += dx
            sq.y += dy
            self.move(self._tag(sq), dx, dy)
            self._last = (x, y)
            self._update_links()
        elif mode == "resize":
            sq = self.selected_square
            new = max(30, self._orig + max(x - self._anchor[0], y - self._anchor[1]))
            if new != sq.size:
                sq.size = new
                self._draw_square(sq, fast=True)
                self._update_links()
        elif mode == "folder":
            fd = self.selected_folder
            fd.x += dx
            fd.y += dy
            self.move(self._tag(fd), dx, dy)
            for s in self._members(fd):          # le contenu suit le dossier
                s.x += dx
                s.y += dy
                if not fd.collapsed:
                    self.move(self._tag(s), dx, dy)
            self._last = (x, y)
            self._update_links()
        elif mode == "bg_move":
            self.bg_x += dx
            self.bg_y += dy
            self.move("background", dx, dy)
            self._last = (x, y)
        elif mode == "bg_resize":
            self.bg_width = max(50, self._orig[0] + x - self._anchor[0])
            self.bg_height = max(50, self._orig[1] + y - self._anchor[1])
            self._redraw_background(fast=True)
        elif mode == "connect":
            if self.connect_line and self.connecting_from:
                cx, cy = self.connecting_from.center()
                self.coords(self.connect_line, cx, cy, x, y)

    def _on_release(self, event):
        x, y = self._pos(event)
        mode, self._mode = self._mode, None

        if mode == "connect":
            src = self.connecting_from
            target = self._square_at(x, y)
            if src and target and target.id != src.id:
                self.add_link(src.id, target.id)
            self._cancel_connect()
            self._update_links()
        elif mode == "move":
            self._assign_folder(self.selected_square)
        elif mode == "resize":
            self._draw_square(self.selected_square)      # rendu haute qualité
            self._assign_folder(self.selected_square)
        elif mode == "bg_resize":
            self._redraw_background()                    # rendu haute qualité

    def _on_double_click(self, event):
        x, y = self._pos(event)
        sq = self._square_at(x, y)
        if sq:                                           # début d'une connexion
            self._mode = "connect"
            self.connecting_from = sq
            cx, cy = sq.center()
            self.connect_line = self.create_line(cx, cy, cx, cy, fill=LOCK_COLOR, width=2,
                                                 dash=(4, 2), tags="connect_line")
            return
        fd = self._folder_at(x, y)
        if fd:
            fd.collapsed = not fd.collapsed
            self._draw_folder(fd)
            for s in self._members(fd):
                self._draw_square(s)
            self._update_links()
            self._restack()

    def _on_right_click(self, event):
        x, y = self._pos(event)
        self.context_menu_x, self.context_menu_y = x, y
        sq = self._square_at(x, y)
        if sq:
            self._select(sq=sq)
        else:
            fd = self._folder_at(x, y)
            self._select(fd=fd) if fd else self._select()
        try:
            self.context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.context_menu.grab_release()

    def _on_motion(self, event):
        x, y = self._pos(event)
        sq = self._square_at(x, y)
        if sq is not self.hovered_square:
            self.hovered_square = sq
            self._update_links()

    def _on_leave(self, event):
        if self.hovered_square is not None and self._mode != "connect":
            self.hovered_square = None
            self._update_links()

    def _cancel_connect(self):
        if self.connect_line:
            self.delete(self.connect_line)
        self.connect_line = None
        self.connecting_from = None

    def _assign_folder(self, sq):
        """Un carré lâché sur un dossier ouvert en devient membre."""
        if sq is None:
            return
        cx, cy = sq.center()
        target = None
        for fd in reversed(self.folders):
            if not fd.collapsed and fd.contains(cx, cy):
                target = fd
                break
        sq.folder_id = target.id if target else None

    # ------------------------------------------------------------------
    # Actions du menu contextuel
    # ------------------------------------------------------------------
    def _add_square_at_cursor(self):
        self.add_square(self.context_menu_x, self.context_menu_y, size=self.square_size)

    def _add_folder_at_cursor(self):
        self.add_folder(self.context_menu_x, self.context_menu_y)

    def _selected(self):
        return self.selected_square or self.selected_folder

    def _change_color(self):
        obj = self._selected()
        if not obj:
            return
        from dialogs import ask_color
        color = ask_color(self.winfo_toplevel(), obj.color)
        if color:
            obj.color = color
            (self._draw_square if isinstance(obj, Square) else self._draw_folder)(obj)

    def _rename(self):
        obj = self._selected()
        if not obj:
            return
        from dialogs import ask_string
        is_sq = isinstance(obj, Square)
        current = obj.name if is_sq else obj.title
        name = ask_string(self.winfo_toplevel(), "Renommer", "Nouveau nom :", current)
        if name:
            if is_sq:
                obj.name = name
                self._draw_square(obj)
            else:
                obj.title = name
                self._draw_folder(obj)

    def _toggle_lock(self):
        sq = self.selected_square
        if sq:
            sq.locked = not sq.locked
            self._draw_square(sq)

    def _delete_selected(self):
        sq, fd = self.selected_square, self.selected_folder
        if sq:
            self.delete(self._tag(sq))
            self.squares = [s for s in self.squares if s.id != sq.id]
            self.links = [l for l in self.links if sq.id not in (l.source_id, l.target_id)]
            self._images.pop(sq.id, None)
            self._photo_cache.pop(sq.id, None)
            if self.hovered_square is sq:
                self.hovered_square = None
        elif fd:
            for s in self._members(fd):                  # le contenu est libéré
                s.folder_id = None
            self.delete(self._tag(fd))
            self.folders = [f for f in self.folders if f.id != fd.id]
        else:
            return
        self.selected_square = self.selected_folder = None
        self._update_links()

    def toggle_background_lock(self):
        if not self.background_image:
            return
        self.bg_locked = not self.bg_locked
        self._redraw_background()

    def get_background_state(self):
        return {
            "image": self.background_image or "",
            "x": round(self.bg_x),
            "y": round(self.bg_y),
            "width": round(self.bg_width),
            "height": round(self.bg_height),
            "locked": bool(getattr(self, "bg_locked", False)),
        }

    def set_default_square_size(self):
        from dialogs import ask_string
        value = ask_string(self.winfo_toplevel(), "Taille des carrés", "Taille par défaut (10 à 500) :", str(self.square_size))
        if value is None:
            return
        try:
            size = int(float(value))
        except (ValueError, OverflowError):
            return
        self.square_size = max(10, min(500, size))

    def set_link_width(self):
        from dialogs import ask_string
        value = ask_string(self.winfo_toplevel(), "Épaisseur des liens", "Largeur au survol (1 à 20) :", str(getattr(self, "link_width", 3)))
        if value is None:
            return
        try:
            width = int(float(value))
        except (ValueError, OverflowError):
            return
        self.link_width = max(1, min(20, width))
