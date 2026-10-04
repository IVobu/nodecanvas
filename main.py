import json
import os
import tkinter as tk
from tkinter import filedialog, messagebox
from canvas_widget import NodeCanvas, _load_settings, _save_settings
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
        self._recent_menu = tk.Menu(file_menu, tearoff=0)
        file_menu.add_cascade(label="Récents", menu=self._recent_menu)
        self._refresh_recent_menu()
        file_menu.add_separator()
        file_menu.add_command(label="Quitter", command=self.root.quit)

        edit_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Édition", menu=edit_menu)
        edit_menu.add_command(label="Annuler (Ctrl+Z)", command=self.canvas.undo)
        edit_menu.add_command(label="Rétablir (Ctrl+Maj+Z)", command=self.canvas.redo)
        edit_menu.add_separator()
        edit_menu.add_command(label="Copier les carrés (Ctrl+C)", command=self.canvas.copy_selected)
        edit_menu.add_command(label="Coller les carrés (Ctrl+Maj+V)", command=self.canvas.paste_squares)
        edit_menu.add_command(label="Tout sélectionner (Ctrl+A)", command=self.canvas.select_all_squares)
        edit_menu.add_command(label="Supprimer tous les liens", command=self.canvas.clear_links)
        edit_menu.add_command(label="Supprimer (Suppr)", command=self.canvas._delete_selected)

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
        settings_menu.add_command(label="Taille des carrés…", command=self.canvas.set_square_size)
        settings_menu.add_command(label="Épaisseur des liens…", command=self.canvas.set_link_width)
        settings_menu.add_command(label="Couleur des liens…", command=self.canvas.set_link_color)
        settings_menu.add_separator()
        settings_menu.add_command(label="Carré rapide 1 (touche 1 + clic droit) : couleur…",
                                  command=lambda: self.canvas.set_default_square_color(1))
        settings_menu.add_command(label="Carré rapide 1 (touche 1 + clic droit) : nom…",
                                  command=lambda: self.canvas.set_default_square_name(1))
        settings_menu.add_command(label="Carré rapide 2 (touche 2 + clic droit) : couleur…",
                                  command=lambda: self.canvas.set_default_square_color(2))
        settings_menu.add_command(label="Carré rapide 2 (touche 2 + clic droit) : nom…",
                                  command=lambda: self.canvas.set_default_square_name(2))
        settings_menu.add_separator()
        settings_menu.add_command(label="Annulations max (Ctrl+Z)…", command=self.canvas.set_undo_depth)
        self._bg_block_var = tk.BooleanVar(value=self.canvas.bg_blocks_clicks)
        self.canvas._bg_block_var = self._bg_block_var
        settings_menu.add_checkbutton(label="Fond non cliquable",
                                      variable=self._bg_block_var,
                                      command=self.canvas.toggle_bg_blocks_clicks)

    def _refresh_recent_menu(self):
        self._recent_menu.delete(0, tk.END)
        recents = _load_settings().get("recent_files", [])
        if not recents:
            self._recent_menu.add_command(label="(vide)", state=tk.DISABLED)
        for path in recents:
            self._recent_menu.add_command(label=path, command=lambda p=path: self._load_recent(p))

    def _add_recent(self, filepath):
        data = _load_settings()
        recents = data.get("recent_files", [])
        recents = [p for p in recents if p != filepath]
        recents.insert(0, filepath)
        data["recent_files"] = recents[:10]
        _save_settings(data)
        self._refresh_recent_menu()

    def _load_recent(self, filepath):
        if not os.path.exists(filepath):
            messagebox.showerror("Erreur", f"Fichier introuvable : {filepath}")
            return
        try:
            squares, links, folders, bg, settings = import_json(filepath)
            self.canvas.load_data(squares, links, folders, bg)
            if settings:
                self.canvas.square_size = settings.get("square_size", 60)
                self.canvas.link_width = settings.get("link_width", 3)
                self.canvas.default_link_color = settings.get("link_color", "#888888")
            self._add_recent(filepath)
            messagebox.showinfo("Import", "Import réussi !")
        except Exception as e:
            messagebox.showerror("Erreur", str(e))

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
                self._add_recent(filepath)
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
                self._add_recent(filepath)
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
        root = TkinterDnD.Tk()      # supporte le glisser-déposer de fichiers
    except Exception:
        root = tk.Tk()             # sans tkinterdnd2 : l'application reste utilisable
    NodeCanvasApp(root)
    root.mainloop()
