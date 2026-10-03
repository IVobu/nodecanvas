import tkinter as tk
from models import Square, Link, Folder

try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
    TKDND_AVAILABLE = True
except ImportError:
    TKDND_AVAILABLE = False


class NodeCanvas(tk.Canvas):
    def __init__(self, parent, **kwargs):
        super().__init__(parent, bg="#2D2D2D", highlightthickness=0, **kwargs)
        self.squares = []
        self.links = []
        self.folders = []
        self.background_image = None
        self.bg_photo = None

        self.selected_square = None
        self.hovered_square = None
        self.dragging = False
        self.drag_start = (0, 0)
        self.connecting_from = None
        self.connect_line = None
        self.dragging_folder = None
        self.drag_folder_offset = (0, 0)
        self.panning = False
        self.pan_start = (0, 0)
        self.offset_x = 0
        self.offset_y = 0
        self.square_size = 60

        self.resizing = False
        self.resize_start = (0, 0)
        self.resize_original_size = 0

        self.bg_x = 0
        self.bg_y = 0
        self.bg_width = 0
        self.bg_height = 0
        self.bg_original = None
        self.dragging_bg = False
        self.drag_bg_start = (0, 0)
        self.resizing_bg = False
        self.resize_bg_start = (0, 0)
        self.resize_bg_original = (0, 0)

        self._build_context_menu()
        self._bind_events()
        self._setup_dnd()

    def _build_context_menu(self):
        self.context_menu = tk.Menu(self, tearoff=0)
        self.context_menu.add_command(label="Nouveau carré", command=self._add_square_at_cursor)
        self.context_menu.add_command(label="Nouveau dossier", command=self._add_folder_at_cursor)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Changer couleur", command=self._change_square_color)
        self.context_menu.add_command(label="Renommer", command=self._rename_square)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Coller image (Ctrl+V)", command=self._paste_from_clipboard)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Verrouiller/Déverrouiller", command=self._toggle_lock)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Supprimer", command=self._delete_selected)

    def _bind_events(self):
        self.bind("<Button-1>", self._on_left_click)
        self.bind("<B1-Motion>", self._on_drag)
        self.bind("<ButtonRelease-1>", self._on_release)
        self.bind("<Button-3>", self._on_right_click)
        self.bind("<Double-Button-1>", self._on_double_click)
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<Motion>", self._on_motion)
        self.bind("<Control-v>", lambda e: self._paste_from_clipboard())
        self.bind("<Button-2>", self._on_middle_click)
        self.bind("<B2-Motion>", self._on_pan)
        self.bind("<ButtonRelease-2>", self._on_middle_release)

    def _setup_dnd(self):
        if TKDND_AVAILABLE:
            self.drop_target_register(DND_FILES)
            self.dnd_bind("<<Drop>>", self._on_drop)
            self.dnd_bind("<<DropEnter>>", self._on_drop_enter)
            self.dnd_bind("<<DropLeave>>", self._on_drop_leave)

    def _on_drop_enter(self, event):
        self.config(highlightbackground="#FFD700", highlightthickness=2)

    def _on_drop_leave(self, event):
        self.config(highlightthickness=0)

    def _on_drop(self, event):
        self.config(highlightthickness=0)
        files = event.data.split()
        for f in files:
            f = f.strip("{}")
            if f.lower().endswith((".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp")):
                self._add_image_square(f, event.x_root - self.winfo_rootx(), event.y_root - self.winfo_rooty())

    def _add_image_square(self, filepath, x, y):
        try:
            from PIL import Image, ImageTk
            img = Image.open(filepath)
            img.thumbnail((300, 300), Image.LANCZOS)
            photo = ImageTk.PhotoImage(img)
            sq = Square(x - 150, y - 150, 300, "#3A3A3A", filepath.split("/")[-1].split("\\")[-1], image_path=filepath)
            sq.photo = photo
            self.squares.append(sq)
            self._draw_image_square(sq)
            return sq
        except Exception:
            return None

    def _draw_image_square(self, sq):
        x2, y2 = sq.x + sq.size, sq.y + sq.size
        outline_color = "#FFD700" if sq.locked else "#FFFFFF"
        self.create_rectangle(sq.x, sq.y, x2, y2, fill=sq.color, outline=outline_color, width=3 if sq.locked else 2, tags=("square", sq.id))
        if hasattr(sq, "photo"):
            cx, cy = sq.center()
            self.create_image(cx, cy, image=sq.photo, tags=("square_img", sq.id))
        cx, cy = sq.center()
        self.create_text(cx, sq.y + sq.size - 10, text=sq.name[:12], fill="#FFFFFF", font=("Segoe UI", 7), tags=("square_text", sq.id))
        if not sq.locked:
            handle_size = 10
            self.create_rectangle(x2 - handle_size, y2 - handle_size, x2, y2, fill="#FFD700", outline="#FFFFFF", width=1, tags=("resize_handle", sq.id))

    def _paste_from_clipboard(self):
        try:
            from PIL import ImageGrab, ImageTk
            img = ImageGrab.grabclipboard()
            if img is None:
                return
            img.thumbnail((300, 300), Image.LANCZOS)
            photo = ImageTk.PhotoImage(img)
            x = self.winfo_width() / 2 - 150
            y = self.winfo_height() / 2 - 150
            sq = Square(x, y, 300, "#3A3A3A", "Collage", image_path="clipboard")
            sq.photo = photo
            self.squares.append(sq)
            self._draw_image_square(sq)
        except Exception:
            pass

    def set_background_image(self, filepath):
        if not filepath:
            self.background_image = None
            self.bg_photo = None
            self.bg_x = 0
            self.bg_y = 0
            self.bg_width = 0
            self.bg_height = 0
            self.delete("background")
            return
        try:
            from PIL import Image, ImageTk
            img = Image.open(filepath)
            self.bg_original = img
            self.bg_photo = ImageTk.PhotoImage(img)
            self.bg_x = 0
            self.bg_y = 0
            self.bg_width = img.width
            self.bg_height = img.height
            self.delete("background")
            self.create_image(0, 0, image=self.bg_photo, anchor="nw", tags="background")
            self.tag_lower("background")
            self.background_image = filepath
        except Exception:
            self.background_image = None
            self.bg_photo = None

    def add_square(self, x, y, size=None, color="#4A90D9", name=""):
        if size is None:
            size = self.square_size
        sq = Square(x, y, size, color, name)
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

    def _draw_square(self, sq):
        x2, y2 = sq.x + sq.size, sq.y + sq.size
        self.create_rectangle(sq.x, sq.y, x2, y2, fill=sq.color, outline="#FFFFFF", width=2, tags=("square", sq.id))
        cx, cy = sq.center()
        self.create_text(cx, cy, text=sq.name, fill="#FFFFFF", font=("Segoe UI", 9, "bold"), tags=("square_text", sq.id))

    def _draw_folder(self, fd):
        if fd.collapsed:
            self.create_rectangle(fd.x, fd.y, fd.x + fd.w, fd.y + 30, fill=fd.color, outline="#AAAAAA", width=1, tags=("folder", fd.id))
            self.create_text(fd.x + 10, fd.y + 15, text=f"+ {fd.title}", fill="#333333", anchor="w", font=("Segoe UI", 10, "bold"), tags=("folder_title", fd.id))
        else:
            self.create_rectangle(fd.x, fd.y, fd.x + fd.w, fd.y + fd.h, fill=fd.color, outline="#AAAAAA", width=1, tags=("folder", fd.id))
            self.create_rectangle(fd.x, fd.y, fd.x + fd.w, fd.y + 30, fill="#E8E8E8", outline="#AAAAAA", width=1, tags=("folder_header", fd.id))
            self.create_text(fd.x + 10, fd.y + 15, text=f"- {fd.title}", fill="#333333", anchor="w", font=("Segoe UI", 10, "bold"), tags=("folder_title", fd.id))

    def _redraw_background(self):
        if not self.background_image:
            return
        try:
            from PIL import Image, ImageTk
            img = self.bg_original.resize((int(self.bg_width), int(self.bg_height)), Image.LANCZOS)
            self.bg_photo = ImageTk.PhotoImage(img)
            self.delete("background")
            self.create_image(self.bg_x, self.bg_y, image=self.bg_photo, anchor="nw", tags="background")
            self.tag_lower("background")
        except Exception:
            pass

    def _redraw(self):
        self.delete("square", "square_text", "square_img", "resize_handle", "folder", "folder_header", "folder_title", "link", "connect_line")
        self._redraw_background()
        for fd in self.folders:
            self._draw_folder(fd)
        for sq in self.squares:
            if hasattr(sq, "photo"):
                self._draw_image_square(sq)
            else:
                self._draw_square(sq)
        self._draw_visible_links()

    def _draw_visible_links(self):
        visible = set()
        if self.hovered_square:
            visible.add(self.hovered_square.id)
        for sq in self.squares:
            if self._is_hovered(sq):
                visible.add(sq.id)
        for ln in self.links:
            if ln.source_id in visible or ln.target_id in visible:
                self._draw_link(ln)

    def _is_hovered(self, sq):
        return self.hovered_square and self.hovered_square.id == sq.id

    def _draw_link(self, ln):
        src = self._find_square(ln.source_id)
        tgt = self._find_square(ln.target_id)
        if not src or not tgt:
            return
        x1, y1 = src.center()
        x2, y2 = tgt.center()
        self.create_line(x1, y1, x2, y2, fill=ln.color, width=3, tags="link")

    def _find_square(self, sq_id):
        for sq in self.squares:
            if sq.id == sq_id:
                return sq
        return None

    def _on_left_click(self, event):
        x, y = event.x, event.y
        if self.background_image and self.bg_x <= x <= self.bg_x + self.bg_width and self.bg_y <= y <= self.bg_y + self.bg_height:
            handle_size = 10
            if self.bg_x + self.bg_width - handle_size <= x <= self.bg_x + self.bg_width and self.bg_y + self.bg_height - handle_size <= y <= self.bg_y + self.bg_height:
                self.resizing_bg = True
                self.resize_bg_start = (x, y)
                self.resize_bg_original = (self.bg_width, self.bg_height)
                return
            self.dragging_bg = True
            self.drag_bg_start = (x - self.bg_x, y - self.bg_y)
            return
        sq = self._square_at(x, y)
        if sq:
            if self.connecting_from and self.connecting_from.id != sq.id:
                self.add_link(self.connecting_from.id, sq.id)
                self._cancel_connect()
                self._redraw()
                return
            if self.connecting_from and self.connecting_from.id == sq.id:
                self._cancel_connect()
                self._redraw()
                return
            self.selected_square = sq
            if not sq.locked:
                handle_size = 10
                x2, y2 = sq.x + sq.size, sq.y + sq.size
                if x2 - handle_size <= x <= x2 and y2 - handle_size <= y <= y2:
                    self.resizing = True
                    self.resize_start = (x, y)
                    self.resize_original_size = sq.size
                    return
                self.dragging = True
                self.drag_start = (x - sq.x, y - sq.y)
            self.connecting_from = sq
            cx, cy = sq.center()
            self.connect_line = self.create_line(cx, cy, cx, cy, fill="#FFD700", width=2, dash=(4, 2), tags="connect_line")
            return
        fd = self._folder_at(x, y)
        if fd:
            if fd.header_contains(x, y):
                self.dragging_folder = fd
                self.drag_folder_offset = (x - fd.x, y - fd.y)
                return
        self.selected_square = None
        self._cancel_connect()
        self._redraw()

    def _on_drag(self, event):
        x, y = event.x, event.y
        if self.dragging_bg:
            self.bg_x = x - self.drag_bg_start[0]
            self.bg_y = y - self.drag_bg_start[1]
            self._redraw_background()
        elif self.resizing_bg:
            dx = x - self.resize_bg_start[0]
            dy = y - self.resize_bg_start[1]
            self.bg_width = max(50, self.resize_bg_original[0] + dx)
            self.bg_height = max(50, self.resize_bg_original[1] + dy)
            self._redraw_background()
        elif self.resizing and self.selected_square:
            dx = x - self.resize_start[0]
            dy = y - self.resize_start[1]
            new_size = max(30, self.resize_original_size + max(dx, dy))
            self.selected_square.size = new_size
            self._redraw()
        elif self.dragging and self.selected_square:
            self._cancel_connect()
            self.selected_square.x = x - self.drag_start[0]
            self.selected_square.y = y - self.drag_start[1]
            self._redraw()
        elif self.dragging_folder:
            self.dragging_folder.x = x - self.drag_folder_offset[0]
            self.dragging_folder.y = y - self.drag_folder_offset[1]
            self._redraw()
        elif self.connecting_from:
            self._update_connect_line(x, y)

    def _on_release(self, event):
        self.dragging = False
        self.dragging_folder = None
        self.resizing = False
        self.dragging_bg = False
        self.resizing_bg = False
        self._redraw()

    def _on_middle_click(self, event):
        self.scan_mark(event.x, event.y)

    def _on_pan(self, event):
        self.scan_dragto(event.x, event.y, gain=1)

    def _on_middle_release(self, event):
        pass

    def _on_right_click(self, event):
        x, y = event.x, event.y
        self.context_menu_x = x
        self.context_menu_y = y
        sq = self._square_at(x, y)
        if sq:
            self.selected_square = sq
            self._redraw()
        try:
            self.context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.context_menu.grab_release()

    def _on_double_click(self, event):
        x, y = event.x, event.y
        fd = self._folder_at(x, y)
        if fd:
            fd.collapsed = not fd.collapsed
            self._redraw()

    def _on_enter(self, event):
        pass

    def _on_leave(self, event):
        self.hovered_square = None
        self._redraw()

    def _on_motion(self, event):
        x, y = event.x, event.y
        sq = self._square_at(x, y)
        if sq != self.hovered_square:
            self.hovered_square = sq
            self._redraw()

    def _square_at(self, x, y):
        for sq in reversed(self.squares):
            if sq.contains(x, y):
                return sq
        return None

    def _folder_at(self, x, y):
        for fd in reversed(self.folders):
            if fd.contains(x, y):
                return fd
        return None

    def _start_connect(self, sq):
        self.connecting_from = sq
        cx, cy = sq.center()
        self.connect_line = self.create_line(cx, cy, cx, cy, fill="#FFD700", width=2, dash=(4, 2), tags="connect_line")

    def _update_connect_line(self, x, y):
        if self.connect_line and self.connecting_from:
            cx, cy = self.connecting_from.center()
            self.coords(self.connect_line, cx, cy, x, y)

    def _cancel_connect(self):
        if self.connect_line:
            self.delete(self.connect_line)
            self.connect_line = None
        self.connecting_from = None

    def _add_square_at_cursor(self):
        x = getattr(self, "context_menu_x", 200)
        y = getattr(self, "context_menu_y", 200)
        self.add_square(x, y, size=self.square_size)

    def _add_folder_at_cursor(self):
        x = getattr(self, "context_menu_x", 200)
        y = getattr(self, "context_menu_y", 200)
        self.add_folder(x, y)

    def _change_square_color(self):
        if self.selected_square:
            from dialogs import ask_color
            color = ask_color(self.winfo_toplevel(), self.selected_square.color)
            if color:
                self.selected_square.color = color
                self._redraw()

    def _rename_square(self):
        if self.selected_square:
            from dialogs import ask_string
            name = ask_string(self.winfo_toplevel(), "Renommer", "Nouveau nom :", self.selected_square.name)
            if name:
                self.selected_square.name = name
                self._redraw()

    def _toggle_lock(self):
        if self.selected_square:
            self.selected_square.locked = not self.selected_square.locked
            self._redraw()

    def _delete_selected(self):
        if self.selected_square:
            sq_id = self.selected_square.id
            self.squares = [s for s in self.squares if s.id != sq_id]
            self.links = [l for l in self.links if l.source_id != sq_id and l.target_id != sq_id]
            self.selected_square = None
            self._redraw()

    def load_data(self, squares, links, folders, background_image):
        self.squares = squares
        self.links = links
        self.folders = folders
        self.set_background_image(background_image)
        self._redraw()
