import tkinter as tk
from models import Square, Link, Folder


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

        self._build_context_menu()
        self._bind_events()

    def _build_context_menu(self):
        self.context_menu = tk.Menu(self, tearoff=0)
        self.context_menu.add_command(label="Nouveau carré", command=self._add_square_at_cursor)
        self.context_menu.add_command(label="Nouveau dossier", command=self._add_folder_at_cursor)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Changer couleur", command=self._change_square_color)
        self.context_menu.add_command(label="Renommer", command=self._rename_square)
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

    def set_background_image(self, filepath):
        if not filepath:
            self.background_image = None
            self.bg_photo = None
            self.delete("background")
            return
        try:
            from PIL import Image, ImageTk
            img = Image.open(filepath)
            self.bg_photo = ImageTk.PhotoImage(img)
            self.delete("background")
            self.create_image(0, 0, image=self.bg_photo, anchor="nw", tags="background")
            self.tag_lower("background")
            self.background_image = filepath
        except Exception:
            self.background_image = None
            self.bg_photo = None

    def add_square(self, x, y, size=60, color="#4A90D9", name=""):
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

    def _redraw(self):
        self.delete("square", "square_text", "folder", "folder_header", "folder_title", "link", "connect_line")
        for fd in self.folders:
            self._draw_folder(fd)
        for sq in self.squares:
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
        self.create_line(x1, y1, x2, y2, fill=ln.color, width=2, tags="link")

    def _find_square(self, sq_id):
        for sq in self.squares:
            if sq.id == sq_id:
                return sq
        return None

    def _on_left_click(self, event):
        x, y = event.x, event.y
        sq = self._square_at(x, y)
        if sq:
            self.selected_square = sq
            self.dragging = True
            self.drag_start = (x - sq.x, y - sq.y)
            return
        fd = self._folder_at(x, y)
        if fd:
            if fd.header_contains(x, y):
                self.dragging_folder = fd
                self.drag_folder_offset = (x - fd.x, y - fd.y)
                return
        self.selected_square = None
        self._redraw()

    def _on_drag(self, event):
        x, y = event.x, event.y
        if self.dragging and self.selected_square:
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
        if self.connecting_from:
            x, y = event.x, event.y
            target = self._square_at(x, y)
            if target and target.id != self.connecting_from.id:
                self.add_link(self.connecting_from.id, target.id)
            self._cancel_connect()
        self.dragging = False
        self.dragging_folder = None
        self._redraw()

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
        sq = self._square_at(x, y)
        if sq:
            self._start_connect(sq)
            return
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
        self.add_square(x, y)

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
