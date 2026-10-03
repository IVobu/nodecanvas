import tkinter as tk
from tkinter import colorchooser, simpledialog


def ask_color(parent, initial="#4A90D9"):
    result = colorchooser.askcolor(initialcolor=initial, parent=parent)
    if result and result[1]:
        return result[1]
    return None


def ask_string(parent, title, prompt, initial=""):
    return simpledialog.askstring(title, prompt, parent=parent, initialvalue=initial)


def ask_folder_title(parent, initial="Dossier"):
    return simpledialog.askstring("Nouveau dossier", "Titre du dossier :", parent=parent, initialvalue=initial)
