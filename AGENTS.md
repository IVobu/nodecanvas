# NodeCanvas — Document de passation (AGENTS.md)

## 1. Présentation
Application bureau **Python 3.13 + Tkinter** : canvas de carrés colorés connectés, dossiers repliables, images (drag & drop, presse-papiers), image de fond, sauvegarde JSON.
Repo : https://github.com/IVobu/nodecanvas (public, compte IVobu).

## 2. Structure & environnement
```
nodecanvas/
├── main.py           # Fenêtre Tkinter, menus (Fichier: Export/Import JSON, Fond: charger/retirer)
├── canvas_widget.py  # NOEUD DU PROJET (~465 lignes) — rendu + interactions
├── models.py         # Square (id,x,y,size,color,name,folder_id,image_path,locked), Link, Folder
├── storage.py        # export_json / import_json (format version 1)
├── dialogs.py        # ask_color, ask_string
├── requirements.txt  # Pillow>=10.0.0, tkinterdnd2>=0.4.0
└── assets/           # images de fond
```
- Dossier local : `C:\Users\Nobu\nodecanvas`
- Lancement : `python main.py` (raccourci bureau → `pythonw.exe`, sans console)
- Tests : `python -c "import canvas_widget, main"` (pas de suite de tests)
- Python 3.13.1, Pillow 11.1.0, tkinterdnd2 0.6.3

## 3. Git
- Branche `main`.
- Dernier commit : `eebeab4 Remove pycache and update gitignore` (AVANT les commits de cette session, voir `git log`).
- `gh` CLI authentifié (IVobu). Git identity : `IVobu <ivobu@users.noreply.github.com>`.
- Pousser : `git push -u origin main` (HTTPS, auth via keyring gh).

## 4. Fonctionnalités actuelles (comportement réel)
- Carrés : clic droit → nouveau/supprimer/couleur/nom ; glisser = déplacer ; handle jaune en bas-droite = resize ; `locked` = contour jaune, non déplaçable (menu "Verrouiller/Déverrouiller").
- Connexion : **clic sur carré A puis clic sur carré B** = lien ; lien affiché uniquement au **survol** d'un des carrés connectés (largeur 3). Clic sur le même carré ou sur le vide annule le mode connexion.
- Dossiers : double-clic = replier/déplier ; en-tête glissable.
- Fond : menu "Fond" → charger/retirer ; drag + resize via handle (voir bug B1).
- Images : drop depuis l'explorateur (png/jpg/gif/bmp/**webp**), Ctrl+V presse-papiers, taille max 300px.
- Pan : clic molette (scan_mark/scan_dragto).
- Export/Import JSON manuel (pas d'auto-save).

## 5. BUGS CONNUS (priorité d'intervention)
| # | Bug | Localisation |
|---|-----|--------------|
| B1 | **Le fond intercepte les clics AVANT les carrés** → dès qu'un fond est chargé, aucun carré cliquable. Inverser l'ordre de détection : carrés > dossiers > fond | `canvas_widget.py` `_on_left_click` ~l.264 |
| B2 | **Ctrl+V ne marche jamais** : `Image.LANCZOS` utilisé mais `from PIL import ImageGrab, ImageTk` → NameError avalé silencieusement par `except: pass`. Importer `Image` | `canvas_widget.py` `_paste_from_clipboard` ~l.129 |
| B3 | **L'image ne grandit pas avec le carré** : `sq.photo` affichée à taille naturelle. Régénérer le PhotoImage à `sq.size` depuis le PIL source (LANCZOS) | `canvas_widget.py` `_draw_image_square` |
| B4 | **Lag** : `_redraw()` appelle `_redraw_background()` = resize PIL à CHAQUE survol/clic/drag. Ne redessiner le fond que lorsqu'il change | `canvas_widget.py` `_redraw` ~l.223 |
| B5 | **Import JSON perd les images** : `load_data` ne recharge pas `photo` depuis `image_path` | `canvas_widget.py` `load_data` ~l.460 |
| B6 | **Ligne de connexion fantôme** : `_redraw()` supprime le tag `connect_line` mais `connecting_from` reste actif → état incohérent, pas de feedback visuel | `canvas_widget.py` `_redraw` / `_on_left_click` |
| B7 | Fond : `bg_x/y/width/height` non sauvegardés dans le JSON → position/taille perdues à l'import | `storage.py` / export |
| B8 | Drop : `event.data.split()` casse les chemins avec espaces (parser les blocs `{...}`) | `canvas_widget.py` `_on_drop` ~l.94 |
| B9 | Code mort : `pan_start`, `offset_x/y` (l.29-30), `_start_connect` (l.405), import `os` inutilisé dans `storage.py` | divers |

## 6. FEATURES MANQUANTES (vs spec d'origine)
1. **Dossiers non fonctionnels** : `folder_id` existe dans le modèle mais AUCUNE action "mettre un carré dans un dossier" → les dossiers sont purement décoratifs.
2. **Repli** : les carrés internes ET leurs liens doivent être **masqués** quand le dossier est replié (choix utilisateur). Un lien externe → carré interne dans un dossier replié doit pointer vers le dossier (icône de regroupement).
3. **Supprimer un lien** : impossible (pas d'UI).
4. **Supprimer / renommer / colorer un dossier** : impossible.
5. Pas de raccourcis clavier (Suppr = supprimer sélection, Échap = annuler connexion).
6. Pas d'auto-save (Ctrl+S ou sauvegarde automatique).
7. README obsolète (décrit l'ancien double-clic pour connecter ; pas de mention drag&drop/lock/WebP/presse-papiers).

## 7. Décisions utilisateur à valider
- Priorité : bugs d'abord, puis features manquantes ?
- Fond cliquable uniquement sur zones vides (après correction B1) — OK ?
- Taille initiale des images = taille réelle (au lieu de 300px forcés) ?
- Assignation carré → dossier : menu contextuel ou drag ? Contenu des dossiers repliés : masqués complètement ou seulement les liens ?
- Sauvegarde : auto-save ? images copiées dans `assets/` (chemins relatifs, JSON portable) ?
- Résultat : validez chaque étape avant commit.

## 8. Workflow imposé
1. Implémenter une fonctionnalité / corriger un bug.
2. Lancer un **sous-agent de code review** (qualité, bugs, conventions Python).
3. Corriger les retours du review.
4. Présenter à l'utilisateur → validation explicite.
5. Commit conventionnel (`feat:` / `fix:` / `docs:`) + push.

> **Attention** : des sous-agents sont déjà partis en boucle infinie sur les tâches drag&drop et presse-papiers. Leur prompt doit être **strict et borné** : fichiers précis à modifier, tâche unitaire, interdiction d'itérer au-delà (pas de refactor global, pas de lecture de fichiers hors périmètre), critère de fin explicite.
