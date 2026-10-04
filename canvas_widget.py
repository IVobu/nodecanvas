"""Canvas Tkinter de NodeCanvas.

- Chaque objet est dessiné une fois puis déplacé avec Canvas.move().
- Le modèle est en coordonnées "monde" ; l'affichage = monde * self.zoom.
- Ordre d'empilement stable : fond < dossiers < liens < images < carrés.
- Les tags sont préfixés (un id 100 % numérique serait pris pour un item Tk).
"""
import os
import uuid
import tkinter as tk

from models import Square, Link, Folder

try:
    from PIL import Image, ImageTk, ImageGrab
    PIL_AVAILABLE = True
except ImportError:
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
MAX_BG_SIDE = 3000
MAX_IMG_SIDE = 1024
HANDLE = 12              # poignée de redimensionnement (pixels écran)
HEADER_H = 30            # en-tête d'un dossier ouvert (monde)
ICON_W, ICON_H = 56, 42  # icône d'un dossier fermé (monde)
FOLDER_MIN_W, FOLDER_MIN_H = 120, 80
MIN_ZOOM, MAX_ZOOM = 0.1, 2.0
SELECT_COLOR = "#4FC3F7"
LOCK_COLOR = "#FFD700"


class NodeCanvas(tk.Canvas):
    def __init__(self, parent, **kwargs):
        super().__init__(parent, bg="#2D2D2D", highlightthickness=0, **kwargs)

        # --- données (noms conservés pour storage.py / main.py) ---
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

        # --- vue ---
        self.zoom = 1.0
        self.ignore_locked = False   # True : les éléments verrouillés laissent passer les clics

        # --- interaction ---
        self.selected_square = None
        self.selected_folder = None
        self.hovered_square = None
        self.hovered_folder = None
        self.connecting_from = None
        self.connect_line = None
        self.context_menu_x = 200
        self.context_menu_y = 200
        self._mode = None
        self._last = (0, 0)
        self._anchor_pt = (0, 0)
        self._orig = None
        self._last_link_time = -10000
        self._zoom_job = None
        self._notice_job = None

        # --- caches d'images ---
        self._images = {}
        self._photo_cache = {}

        self._build_context_menu()
        self._bind_events()
        self._setup_dnd()
        self.after(300, self._install_view_menu)

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
        m.add_command(label="Renommer (F2)", command=self._rename)
        m.add_separator()
        m.add_command(label="Coller image (Ctrl+V)", command=self._paste_from_clipboard)
        m.add_separator()
        m.add_command(label="Tourner image…", command=self._rotate_image)
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
        self.bind("<Enter>", lambda e: self.focus_set())
        self.bind("<Leave>", self._on_leave)
        self.bind("<MouseWheel>", self._on_wheel)       # Windows / macOS
        self.bind("<Button-4>", self._on_wheel)         # Linux
        self.bind("<Button-5>", self._on_wheel)
        self.bind("<Control-v>", lambda e: self._paste_from_clipboard())
        self.bind("<Delete>", lambda e: self._delete_selected())
        self.bind("<F2>", lambda e: self._rename())
        self.bind("<Escape>", lambda e: self._cancel_connect())
        self.bind("<Control-Key-0>", lambda e: self.reset_zoom())
        self.bind_all("<Control-l>", lambda e: self.toggle_ignore_locked())
        self.bind_all("<Control-L>", lambda e: self.toggle_ignore_locked())

    def _setup_dnd(self):
        if TKDND_AVAILABLE and hasattr(self, "drop_target_register"):
            self.drop_target_register(DND_FILES)
            self.dnd_bind("<<Drop>>", self._on_drop)
            self.dnd_bind("<<DropEnter>>", lambda e: self.config(highlightbackground="#FFD700", highlightthickness=2))
            self.dnd_bind("<<DropLeave>>", lambda e: self.config(highlightthickness=0))

    def _install_view_menu(self):
        """Ajoute un menu « Affichage » à la barre de menus existante (ou en crée une)."""
        try:
            top = self.winfo_toplevel()
            name = top.cget("menu")
            menubar = top.nametowidget(name) if name else None
            if menubar is None:
                menubar = tk.Menu(top)
                top.config(menu=menubar)
            self._ignore_var = tk.BooleanVar(value=self.ignore_locked)
            vm = tk.Menu(menubar, tearoff=0)
            vm.add_checkbutton(label="Ignorer les éléments verrouillés (Ctrl+L)",
                               variable=self._ignore_var, command=self._on_ignore_menu)
            vm.add_separator()
            vm.add_command(label="Zoom avant", command=lambda: self._zoom_center(1.25))
            vm.add_command(label="Zoom arrière", command=lambda: self._zoom_center(0.8))
            vm.add_command(label="Zoom 100 % (Ctrl+0)", command=self.reset_zoom)
            menubar.add_cascade(label="Affichage", menu=vm)
        except tk.TclError:
            pass

    # ------------------------------------------------------------------
    # Utilitaires
    # ------------------------------------------------------------------
    def _pos(self, event):
        """Coordonnées monde (panoramique et zoom inclus)."""
        return self.canvasx(event.x) / self.zoom, self.canvasy(event.y) / self.zoom

    @staticmethod
    def _tag(obj):
        return ("sq_" if isinstance(obj, Square) else "fd_") + obj.id

    def _handle_w(self):
        return HANDLE / self.zoom

    def _in_handle(self, x, y, rx, ry):
        h = self._handle_w()
        return rx - h <= x <= rx and ry - h <= y <= ry

    def _font(self, base, bold=False):
        size = round(base * self.zoom)
        if size < 5:
            return None
        return ("Segoe UI", size, "bold") if bold else ("Segoe UI", size)

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

    def _is_free_image(self, sq):
        return bool(sq.image_path) and not sq.folder_id

    def _stack(self):
        """Objets du bas vers le haut : images libres < dossiers < carrés (et images rangées dans un dossier)."""
        free = [s for s in self.squares if self._is_free_image(s)]
        top = [s for s in self.squares if not self._is_free_image(s)]
        return free + list(self.folders) + top

    def _folder_rect(self, fd):
        if fd.collapsed:
            return fd.x - 22, fd.y, fd.x + ICON_W + 22, fd.y + ICON_H + 24
        return fd.x, fd.y, fd.x + fd.w, fd.y + fd.h

    def _hit(self, x, y):
        """Objet le plus haut sous le point (même pile que l'affichage)."""
        for obj in reversed(self._stack()):
            if isinstance(obj, Square):
                if not self._visible(obj):
                    continue
                if self.ignore_locked and obj.locked:
                    continue
                if obj.contains(x, y):
                    return obj
            else:
                x1, y1, x2, y2 = self._folder_rect(obj)
                if x1 <= x <= x2 and y1 <= y <= y2:
                    return obj
        return None

    def _square_at(self, x, y):
        obj = self._hit(x, y)
        return obj if isinstance(obj, Square) else None

    def _folder_at(self, x, y):
        obj = self._hit(x, y)
        return obj if isinstance(obj, Folder) else None

    def _anchor(self, sq):
        """Point d'attache d'un lien : le carré, ou l'icône de son dossier s'il est fermé."""
        if sq.folder_id:
            fd = self._folder_by_id(sq.folder_id)
            if fd and fd.collapsed:
                return fd.x + ICON_W / 2, fd.y + ICON_H / 2
        return sq.center()

    def _restack(self):
        self.tag_lower("background")

    def _ask_name(self, title, initial=""):
        try:
            from dialogs import ask_string
        except ImportError:
            return None
        return ask_string(self.winfo_toplevel(), title, "Nom :", initial) or None

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
        self.selected_square = self.selected_folder = None
        self.hovered_square = self.hovered_folder = None
        self.connecting_from = self.connect_line = None
        self.bg_rotation = 0
        self.bg_locked = False
        if isinstance(background_image, dict):
            self.bg_rotation = background_image.get("rotation", 0)
            self.bg_locked = bool(background_image.get("locked", False))
            background_image = background_image.get("image", "")
        self.set_background_image(background_image)
        if self.bg_locked:
            self._redraw_background()
        self._redraw()

    # ------------------------------------------------------------------
    # Zoom / verrouillage global
    # ------------------------------------------------------------------
    def _set_zoom(self, new, sx, sy):
        new = max(MIN_ZOOM, min(MAX_ZOOM, new))
        if abs(new - self.zoom) < 1e-9:
            return
        wx, wy = self.canvasx(sx) / self.zoom, self.canvasy(sy) / self.zoom
        self.zoom = new
        # garde le point sous le curseur immobile
        dx = wx * new - sx - self.canvasx(0)
        dy = wy * new - sy - self.canvasy(0)
        self.scan_mark(0, 0)
        self.scan_dragto(-int(round(dx)), -int(round(dy)), gain=1)
        self._redraw(fast=True)
        if self._zoom_job:
            self.after_cancel(self._zoom_job)
        self._zoom_job = self.after(180, self._redraw)   # rendu haute qualité différé
        self._notice(f"Zoom {round(new * 100)} %")

    def _on_wheel(self, event):
        up = getattr(event, "num", 0) == 4 or getattr(event, "delta", 0) > 0
        self._set_zoom(self.zoom * (1.1 if up else 1 / 1.1), event.x, event.y)

    def _zoom_center(self, factor):
        self._set_zoom(self.zoom * factor, self.winfo_width() / 2, self.winfo_height() / 2)

    def reset_zoom(self):
        self._set_zoom(1.0, self.winfo_width() / 2, self.winfo_height() / 2)

    def toggle_ignore_locked(self):
        self.ignore_locked = not self.ignore_locked
        if hasattr(self, "_ignore_var"):
            self._ignore_var.set(self.ignore_locked)
        self._after_ignore_change()

    def _on_ignore_menu(self):
        self.ignore_locked = bool(self._ignore_var.get())
        self._after_ignore_change()

    def _after_ignore_change(self):
        if self.ignore_locked:
            if self.selected_square is not None and self.selected_square.locked:
                self._select()
            if self.hovered_square is not None and self.hovered_square.locked:
                self.hovered_square = None
                self._update_links()
        self._notice("Éléments verrouillés : clics ignorés" if self.ignore_locked
                     else "Éléments verrouillés : cliquables")

    def _notice(self, text):
        """Petit message temporaire en haut à gauche de la vue."""
        self.delete("notice")
        self.create_text(self.canvasx(12), self.canvasy(10), text=text, anchor="nw",
                         fill="#FFFFFF", font=("Segoe UI", 10, "bold"), tags="notice")
        self.tag_raise("notice")
        if self._notice_job:
            self.after_cancel(self._notice_job)
        self._notice_job = self.after(1500, lambda: self.delete("notice"))

    # ------------------------------------------------------------------
    # Dessin
    # ------------------------------------------------------------------
    def _redraw(self, fast=False):
        self._zoom_job = None
        self.delete("all")
        self.connect_line = None
        self._redraw_background(fast)
        for obj in self._stack():
            if isinstance(obj, Square):
                self._draw_square(obj, fast, keep_order=False)
            else:
                self._draw_folder(obj, keep_order=False)
        self._update_links()
        self._restack()
        if self.connecting_from is not None:
            self._start_connect_line(self.connecting_from)

    def _draw_square(self, sq, fast=False, keep_order=True):
        z = self.zoom
        tag = self._tag(sq)
        self.delete(tag)
        if not self._visible(sq):
            return
        x1, y1, x2, y2 = sq.x * z, sq.y * z, (sq.x + sq.size) * z, (sq.y + sq.size) * z
        if sq is self.selected_square:
            outline, width = SELECT_COLOR, 3
        elif sq.locked:
            outline, width = LOCK_COLOR, 3
        else:
            outline, width = "#FFFFFF", 2
        tags = ("square", tag)
        self.create_rectangle(x1, y1, x2, y2, fill=sq.color, outline=outline, width=width, tags=tags)
        cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
        photo = self._photo_for(sq, fast)
        if photo:
            self.create_image(cx, cy, image=photo, tags=tags)
            font = self._font(7)
            if font:
                self.create_text(cx, y2 - 10 * z, text=sq.name[:12], fill="#FFFFFF", font=font, tags=tags)
        else:
            font = self._font(9, True)
            if font:
                self.create_text(cx, cy, text=sq.name, fill="#FFFFFF", font=font,
                                 width=max(int(sq.size * z) - 6, 10), tags=tags)
        if not sq.locked:
            h = min(HANDLE, (x2 - x1) / 2)
            self.create_rectangle(x2 - h, y2 - h, x2, y2, fill=LOCK_COLOR, outline="#FFFFFF", width=1, tags=tags)
        if keep_order:
            self._restore_order(sq)

    def _restore_order(self, obj):
        """Un objet redessiné reprend sa place dans la pile (il ne saute plus devant)."""
        stack = self._stack()
        try:
            i = stack.index(obj)
        except ValueError:
            return
        mine = self._tag(obj)
        if not self.find_withtag(mine):
            return
        placed = False
        for nxt in stack[i + 1:]:
            t = self._tag(nxt)
            if self.find_withtag(t):
                self.tag_lower(mine, t)
                placed = True
                break
        if not placed:
            self.tag_raise(mine)
        self.tag_lower("background")
        self._place_links()
        if self.connect_line:
            self.tag_raise(self.connect_line)

    def _place_links(self):
        """Les liens passent au-dessus des images et dossiers, sous les carrés."""
        if not self.find_withtag("link"):
            return
        for obj in self._stack():
            if isinstance(obj, Square) and not self._is_free_image(obj):
                t = self._tag(obj)
                if self.find_withtag(t):
                    self.tag_lower("link", t)
                    return
        self.tag_raise("link")

    def _draw_folder(self, fd, keep_order=True):
        z = self.zoom
        tag = self._tag(fd)
        self.delete(tag)
        tags = ("folder", tag)
        selected = fd is self.selected_folder
        outline = SELECT_COLOR if selected else "#AAAAAA"
        width = 3 if selected else 1
        if fd.collapsed:
            x, y = fd.x * z, fd.y * z
            w, h = ICON_W * z, ICON_H * z
            tab = [x, y + 6 * z, x, y, x + 22 * z, y, x + 28 * z, y + 6 * z]
            self.create_polygon(tab, fill="#C9A227", outline=outline, width=width, tags=tags)
            self.create_rectangle(x, y + 6 * z, x + w, y + h, fill=fd.color, outline=outline, width=width, tags=tags)
            self.create_rectangle(x, y + 14 * z, x + w, y + h, fill="#E6C255", outline=outline, width=width, tags=tags)
            count = len(self._members(fd))
            f = self._font(10, True)
            if f and count:
                self.create_text(x + w / 2, y + (14 * z + h) / 2, text=str(count), fill="#333333", font=f, tags=tags)
            f = self._font(10, True)
            if f:
                self.create_text(x + w / 2, y + h + 12 * z, text=fd.title, fill="#FFFFFF", font=f,
                                 width=max(int(ICON_W * z) + 40, 20), tags=tags)
        else:
            x1, y1, x2, y2 = fd.x * z, fd.y * z, (fd.x + fd.w) * z, (fd.y + fd.h) * z
            self.create_rectangle(x1, y1, x2, y2, fill=fd.color, outline=outline, width=width, tags=tags)
            self.create_rectangle(x1, y1, x2, y1 + HEADER_H * z, fill="#E8E8E8", outline="#AAAAAA", width=1, tags=tags)
            f = self._font(10, True)
            if f:
                self.create_text(x1 + 10 * z, y1 + HEADER_H * z / 2, text=f"- {fd.title}", fill="#333333",
                                 anchor="w", font=f, tags=tags)
            hh = min(HANDLE, (x2 - x1) / 2)
            self.create_rectangle(x2 - hh, y2 - hh, x2, y2, fill=LOCK_COLOR, outline="#FFFFFF", width=1, tags=tags)
        if keep_order:
            self._restore_order(fd)

    def _update_links(self):
        """Liens du carré survolé, ou de tout le contenu d'un dossier fermé survolé."""
        self.delete("link")
        focus = set()
        h = self.hovered_square
        if h is not None and self._visible(h):
            focus = {h.id}
        elif self.hovered_folder is not None and self.hovered_folder.collapsed:
            focus = {s.id for s in self._members(self.hovered_folder)}
        if not focus:
            return
        z = self.zoom
        for ln in self.links:
            if ln.source_id not in focus and ln.target_id not in focus:
                continue
            src, tgt = self._find_square(ln.source_id), self._find_square(ln.target_id)
            if not src or not tgt:
                continue
            if src.folder_id and src.folder_id == tgt.folder_id and not self._visible(src):
                continue   # lien interne à un dossier fermé
            x1, y1 = self._anchor(src)
            x2, y2 = self._anchor(tgt)
            self.create_line(x1 * z, y1 * z, x2 * z, y2 * z, fill=ln.color, width=3, tags="link")
        self._place_links()

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
        box = max(int(sq.size * self.zoom) - 4, 1)
        key = (box, fast, sq.rotation)
        cached = self._photo_cache.get(sq.id)
        if cached and cached[0] == key:
            return cached[1]
        scale = min(box / img.width, box / img.height)
        size = (max(int(img.width * scale), 1), max(int(img.height * scale), 1))
        img = img.resize(size, Image.NEAREST if fast else Image.LANCZOS)
        if sq.rotation:
            img = img.rotate(-sq.rotation, expand=True, resample=Image.BICUBIC)
        photo = ImageTk.PhotoImage(img)
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

    def _view_center_world(self):
        z = self.zoom
        return self.canvasx(self.winfo_width() / 2) / z, self.canvasy(self.winfo_height() / 2) / z

    def _paste_from_clipboard(self):
        if not PIL_AVAILABLE:
            return
        try:
            data = ImageGrab.grabclipboard()
        except Exception:
            return
        if data is None:
            return
        cx, cy = self._view_center_world()
        if isinstance(data, list):
            for i, f in enumerate(p for p in data if str(p).lower().endswith(IMAGE_EXT)):
                self._add_image_square(str(f), cx + 20 * i, cy + 20 * i)
            return
        try:
            os.makedirs(ASSETS_DIR, exist_ok=True)
            path = os.path.join(ASSETS_DIR, f"paste_{uuid.uuid4().hex[:8]}.png")
            data.save(path)
        except Exception:
            return
        self._add_image_square(path, cx, cy)

    def _on_drop(self, event):
        self.config(highlightthickness=0)
        z = self.zoom
        x = self.canvasx(event.x_root - self.winfo_rootx()) / z
        y = self.canvasy(event.y_root - self.winfo_rooty()) / z
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
        self.bg_rotation = 0
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
        z = self.zoom
        size = (max(int(self.bg_width * z), 1), max(int(self.bg_height * z), 1))
        img = self.bg_original
        if size != img.size:
            img = img.resize(size, Image.NEAREST if fast else Image.LANCZOS)
        if getattr(self, "bg_rotation", 0):
            img = img.rotate(-self.bg_rotation, expand=True, resample=Image.BICUBIC)
        self.bg_photo = ImageTk.PhotoImage(img)
        self.create_image(self.bg_x * z, self.bg_y * z, image=self.bg_photo, anchor="nw", tags="background")
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
    # Souris
    # ------------------------------------------------------------------
    def _on_left_click(self, event):
        self.focus_set()
        x, y = self._pos(event)
        self._mode = None

        # connexion en attente (double-clic sur un carré) : le clic suivant choisit la cible
        if self.connecting_from is not None:
            src = self.connecting_from
            target = self._square_at(x, y)
            self._cancel_connect()
            if target and target.id != src.id:
                self.add_link(src.id, target.id)
                self._last_link_time = event.time
                self._update_links()
            return

        sq = self._square_at(x, y)
        if sq:
            self._select(sq=sq)
            if not sq.locked:
                if self._in_handle(x, y, sq.x + sq.size, sq.y + sq.size):
                    self._mode, self._anchor_pt, self._orig = "resize", (x, y), sq.size
                else:
                    self._mode, self._last = "move", (x, y)
            return

        fd = self._folder_at(x, y)
        if fd:
            self._select(fd=fd)
            if not fd.collapsed and self._in_handle(x, y, fd.x + fd.w, fd.y + fd.h):
                self._mode, self._anchor_pt, self._orig = "folder_resize", (x, y), (fd.w, fd.h)
            elif fd.collapsed or y <= fd.y + HEADER_H:
                self._mode, self._last = "folder", (x, y)
            return

        self._select()
        if self._bg_hit(x, y):
            if self._in_handle(x, y, self.bg_x + self.bg_width, self.bg_y + self.bg_height):
                self._mode, self._anchor_pt = "bg_resize", (x, y)
                self._orig = (self.bg_width, self.bg_height)
            else:
                self._mode, self._last = "bg_move", (x, y)

    def _on_drag(self, event):
        mode = self._mode
        if mode is None:
            return
        x, y = self._pos(event)
        z = self.zoom
        dx, dy = x - self._last[0], y - self._last[1]

        if mode == "move":
            sq = self.selected_square
            sq.x += dx
            sq.y += dy
            self.move(self._tag(sq), dx * z, dy * z)
            self._last = (x, y)
            self._update_links()
        elif mode == "resize":
            sq = self.selected_square
            new = max(30, self._orig + max(x - self._anchor_pt[0], y - self._anchor_pt[1]))
            if new != sq.size:
                sq.size = new
                self._draw_square(sq, fast=True)
                self._update_links()
        elif mode == "folder":
            fd = self.selected_folder
            fd.x += dx
            fd.y += dy
            self.move(self._tag(fd), dx * z, dy * z)
            for s in self._members(fd):
                s.x += dx
                s.y += dy
                if not fd.collapsed:
                    self.move(self._tag(s), dx * z, dy * z)
            self._last = (x, y)
            self._update_links()
        elif mode == "folder_resize":
            fd = self.selected_folder
            fd.w = max(FOLDER_MIN_W, self._orig[0] + x - self._anchor_pt[0])
            fd.h = max(FOLDER_MIN_H, self._orig[1] + y - self._anchor_pt[1])
            self._draw_folder(fd)
        elif mode == "bg_move":
            self.bg_x += dx
            self.bg_y += dy
            self.move("background", dx * z, dy * z)
            self._last = (x, y)
        elif mode == "bg_resize":
            self.bg_width = max(50, self._orig[0] + x - self._anchor_pt[0])
            self.bg_height = max(50, self._orig[1] + y - self._anchor_pt[1])
            self._redraw_background(fast=True)
        elif mode == "connect":
            self._update_connect_line(x, y)

    def _on_release(self, event):
        x, y = self._pos(event)
        mode, self._mode = self._mode, None

        if mode == "connect":
            src = self.connecting_from
            target = self._square_at(x, y)
            if src and target and target.id != src.id:       # glisser-déposer
                self.add_link(src.id, target.id)
                self._cancel_connect()
                self._update_links()
            # sinon : on reste en attente d'un clic sur le second carré
        elif mode == "move":
            self._assign_folder(self.selected_square)
        elif mode == "resize":
            self._draw_square(self.selected_square)
            self._assign_folder(self.selected_square)
        elif mode == "bg_resize":
            self._redraw_background()

    def _on_double_click(self, event):
        x, y = self._pos(event)
        sq = self._square_at(x, y)
        if sq:
            if event.time - self._last_link_time < 500:   # fin d'un double-clic sur la cible
                return
            self._cancel_connect()
            self._mode = "connect"
            self.connecting_from = sq
            self._start_connect_line(sq)
            return
        fd = self._folder_at(x, y)
        if fd:
            fd.collapsed = not fd.collapsed
            self.hovered_folder = fd if fd.collapsed else None
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
            if fd:
                self._select(fd=fd)
            else:
                self._select()
        try:
            self.context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.context_menu.grab_release()

    def _on_motion(self, event):
        x, y = self._pos(event)
        sq = self._square_at(x, y)
        fd = None
        if sq is None:
            f = self._folder_at(x, y)
            fd = f if (f is not None and f.collapsed) else None
        if sq is not self.hovered_square or fd is not self.hovered_folder:
            self.hovered_square, self.hovered_folder = sq, fd
            self._update_links()
        if self.connecting_from is not None and self._mode is None:
            self._update_connect_line(x, y)

    def _on_leave(self, event):
        if self._mode != "connect" and (self.hovered_square or self.hovered_folder):
            self.hovered_square = self.hovered_folder = None
            self._update_links()

    # --- ligne de connexion -------------------------------------------
    def _start_connect_line(self, sq):
        z = self.zoom
        cx, cy = sq.center()
        self.connect_line = self.create_line(cx * z, cy * z, cx * z, cy * z, fill=LOCK_COLOR, width=2,
                                             dash=(4, 2), tags="connect_line")

    def _update_connect_line(self, x, y):
        if self.connect_line and self.connecting_from:
            z = self.zoom
            cx, cy = self.connecting_from.center()
            self.coords(self.connect_line, cx * z, cy * z, x * z, y * z)
            self.tag_raise(self.connect_line)

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
        new_id = target.id if target else None
        if new_id != sq.folder_id:
            sq.folder_id = new_id
            self._restore_order(sq)

    # ------------------------------------------------------------------
    # Actions (menu contextuel / raccourcis)
    # ------------------------------------------------------------------
    def _add_square_at_cursor(self):
        name = self._ask_name("Nouveau carré")
        self.add_square(self.context_menu_x, self.context_menu_y, size=self.square_size, name=name or "")

    def _add_folder_at_cursor(self):
        title = self._ask_name("Nouveau dossier", "Dossier")
        self.add_folder(self.context_menu_x, self.context_menu_y, title=title or "Dossier")

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
        is_sq = isinstance(obj, Square)
        name = self._ask_name("Renommer", obj.name if is_sq else obj.title)
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
            if self.ignore_locked and sq.locked:
                self._select()

    def _delete_selected(self):
        sq, fd = self.selected_square, self.selected_folder
        if sq:
            if self.connecting_from is sq:
                self._cancel_connect()
            self.delete(self._tag(sq))
            self.squares = [s for s in self.squares if s.id != sq.id]
            self.links = [l for l in self.links if sq.id not in (l.source_id, l.target_id)]
            self._images.pop(sq.id, None)
            self._photo_cache.pop(sq.id, None)
            if self.hovered_square is sq:
                self.hovered_square = None
        elif fd:
            for s in self._members(fd):
                s.folder_id = None
                self._draw_square(s)
            self.delete(self._tag(fd))
            self.folders = [f for f in self.folders if f.id != fd.id]
            if self.hovered_folder is fd:
                self.hovered_folder = None
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
            "rotation": round(getattr(self, "bg_rotation", 0)),
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

    def _rotate_image(self):
        sq = self.selected_square
        if not sq or not sq.image_path:
            return
        from dialogs import ask_string
        value = ask_string(self.winfo_toplevel(), "Rotation", "Angle en degrés :", str(sq.rotation))
        if value is None:
            return
        try:
            angle = float(value)
        except (ValueError, OverflowError):
            return
        sq.rotation = angle % 360
        self._photo_cache.pop(sq.id, None)
        self._draw_square(sq)

    def _rotate_background(self):
        if not self.background_image:
            return
        from dialogs import ask_string
        value = ask_string(self.winfo_toplevel(), "Rotation du fond", "Angle en degrés :", str(getattr(self, "bg_rotation", 0)))
        if value is None:
            return
        try:
            angle = float(value)
        except (ValueError, OverflowError):
            return
        self.bg_rotation = angle % 360
        self._redraw_background()
