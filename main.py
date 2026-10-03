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

    def _export(self):
        filepath = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON files", "*.json")])
        if filepath:
            try:
                export_json(self.canvas.squares, self.canvas.links, self.canvas.folders, self.canvas.background_image, filepath)
                messagebox.showinfo("Export", "Export réussi !")
            except Exception as e:
                messagebox.showerror("Erreur", str(e))

    def _import(self):
        filepath = filedialog.askopenfilename(filetypes=[("JSON files", "*.json")])
        if filepath:
            try:
                squares, links, folders, bg = import_json(filepath)
                self.canvas.load_data(squares, links, folders, bg)
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
