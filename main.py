import tkinter as tk
from tkinter import filedialog, messagebox
from canvas_widget import NodeCanvas
from storage import export_json, import_json


class NodeCanvasApp:
    def __init__(self, root):
        self.root = root
        self.root.title("NodeCanvas")
        self.root.geometry("1200x800")
        self.root.configure(bg="#1E1E1E")

        self.canvas = NodeCanvas(self.root, width=1200, height=800)
        self.canvas.pack(fill=tk.BOTH, expand=True)

        self._build_menu()

    def _build_menu(self):
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)

        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Fichier", menu=file_menu)
        file_menu.add_command(label="Exporter JSON", command=self._export)
        file_menu.add_command(label="Importer JSON", command=self._import)
        file_menu.add_separator()
        file_menu.add_command(label="Quitter", command=self.root.quit)

        bg_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Fond", menu=bg_menu)
        bg_menu.add_command(label="Charger image de fond", command=self._load_background)
        bg_menu.add_command(label="Retirer image de fond", command=self._remove_background)
        bg_menu.add_separator()
        bg_menu.add_command(label="Tourner le fond…", command=self.canvas._rotate_background)
        bg_menu.add_separator()
        bg_menu.add_command(label="Verrouiller/Déverrouiller le fond", command=self.canvas.toggle_background_lock)

        settings_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Réglages", menu=settings_menu)
        settings_menu.add_command(label="Taille par défaut des carrés…", command=self.canvas.set_default_square_size)
        settings_menu.add_command(label="Épaisseur des liens au survol…", command=self.canvas.set_link_width)

    def _export(self):
        filepath = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON files", "*.json")])
        if filepath:
            try:
                settings = {
                    "link_color": getattr(self.canvas, "default_link_color", "#888888"),
                    "square_size": self.canvas.square_size,
                    "link_width": getattr(self.canvas, "link_width", 3),
                }
                export_json(self.canvas.squares, self.canvas.links, self.canvas.folders, self.canvas.get_background_state(), filepath, settings)
                messagebox.showinfo("Export", "Export réussi !")
            except Exception as e:
                messagebox.showerror("Erreur", str(e))

    def _import(self):
        filepath = filedialog.askopenfilename(filetypes=[("JSON files", "*.json")])
        if filepath:
            try:
                squares, links, folders, bg, settings = import_json(filepath)
                self.canvas.load_data(squares, links, folders, bg)
                if settings:
                    self.canvas.square_size = settings.get("square_size", 60)
                    self.canvas.link_width = settings.get("link_width", 3)
                    self.canvas.default_link_color = settings.get("link_color", "#888888")
                messagebox.showinfo("Import", "Import réussi !")
            except Exception as e:
                messagebox.showerror("Erreur", str(e))

    def _load_background(self):
        filepath = filedialog.askopenfilename(filetypes=[("Images", "*.png *.jpg *.jpeg *.gif *.bmp *.webp")])
        if filepath:
            self.canvas.set_background_image(filepath)

    def _remove_background(self):
        self.canvas.set_background_image(None)


if __name__ == "__main__":
    try:
        from tkinterdnd2 import TkinterDnD
        root = TkinterDnD.Tk()
    except ImportError:
        root = tk.Tk()
    app = NodeCanvasApp(root)
    root.mainloop()
