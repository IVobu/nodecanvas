# NodeCanvas — Document de passation (AGENTS.md)

## 1. Présentation
Application bureau **Python 3.13 + Tkinter** : canvas de carrés colorés connectés, dossiers repliables, images (drag & drop, presse-papiers), image de fond, sauvegarde JSON.
Repo : https://github.com/IVobu/nodecanvas (public, compte IVobu).

## 2. Structure & environnement
```
nodecanvas/
├── main.py           # Fenêtre Tkinter, menus (Fichier: Export/Import JSON, Fond: charger/retirer)
├── canvas_widget.py  # NOEUD DU PROJET (~567 lignes) — rendu + interactions
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
- Carrés : clic droit → nouveau/supprimer/couleur/nom ; glisser = déplacer ; **Alt + handle jaune en bas-droite = resize** ; `locked` = contour jaune, non déplaçable (menu "Verrouiller/Déverrouiller"). Création sans fenêtre de nom (renommage via F2 ou menu contextuel). Couleur des liens modifiable via menu contextuel "Changer couleur du lien…".
- Connexion : **double-clic sur carré A puis clic sur carré B** = lien (ou drag & drop) ; lien affiché uniquement au **survol** d'un des carrés connectés. Ligne dorée pointillée du centre de A vers le curseur pendant le mode connexion.
- Dossiers : double-clic = replier/déplier (contenu masqué, icône avec compteur) ; en-tête glissable ; drop d'un carré sur un dossier ouvert = assignation ; resize possible.
- Fond : menu "Fond" → charger/retirer/**verrouiller-déverrouiller** ; drag + handle visible en bas-droite (carré doré) ; état (x,y,w,h,locked) sauvegardé en JSON. Le verrou bloque drag/resize (contour doré pointillé).
- Réglages : menu "Réglages" → taille par défaut des carrés (10-500), épaisseur des liens au survol (1-20).
- Images : drop depuis l'explorateur (png/jpg/gif/bmp/**webp**), Ctrl+V presse-papiers (sauvegarde dans assets/), images redimensionnées dynamiquement avec le carré.
- **Rotation** : poignée de rotation au-dessus du carré sélectionné (drag), R/Maj+R = ±90° (avec animation), 0 = réinitialiser. Aimantation 45°, Maj = pas 15°.
- **Flip** : H = miroir horizontal, V = miroir vertical (par rapport à l'écran, même après rotation).
- **Hit-test avec rotation** : déplacement, resize et rotation tiennent compte de l'angle du carré.
- **Paramètres persistés** : couleur des liens, taille des carrés, épaisseur des liens → sauvegardés dans le JSON.
- **Zoom** : molette (0.1x–2.0x), Ctrl+0 = reset, menu "Affichage" → zoom avant/arrière/100%.
- **Mode "Ignorer les verrous"** : Ctrl+L ou menu "Affichage" → les éléments verrouillés laissent passer les clics.
- **Raccourcis clavier** : Suppr = supprimer, F2 = renommer, Échap = annuler connexion, Ctrl+V = coller, Ctrl+0 = zoom 100%.
- Pan : clic molette (scan_mark/scan_dragto) — les clics sont convertis en coordonnées canvas (`canvasx/canvasy`), donc pas de décalage.
- Export/Import JSON manuel (pas d'auto-save).
- **Performance** : rendu incrémental (Canvas.move) + tags préfixés (sq_, fd_) + zoom avec coordonnées monde/écran.
- **Ordre de pile** : images libres < dossiers < carrés (hit-test et rendu cohérents).

## 5. BUGS CONNUS (priorité d'intervention)
| # | Bug | Statut |
|---|-----|--------|
| B1 | Le fond intercepte les clics avant les carrés | **CORRIGÉ** |
| B2 | Ctrl+V ne marche jamais (NameError Image) | **CORRIGÉ** |
| B3 | L'image ne grandit pas avec le carré | **CORRIGÉ** |
| B4 | Lag : fond redessiné à chaque survol | **CORRIGÉ** |
| B5 | Import JSON perd les images | **CORRIGÉ** |
| B6 | Ligne de connexion fantôme | **CORRIGÉ** |
| B7 | Fond non sauvegardé dans le JSON | **CORRIGÉ** |
| B8 | Drop : chemins avec espaces cassés | **CORRIGÉ** |
| B9 | Code mort `os` dans storage.py | **CORRIGÉ** |
| B10 | Pan molette décalait les clics | **CORRIGÉ** |

## 6. FEATURES MANQUANTES (vs spec d'origine)
1. **Supprimer un lien** : impossible (pas d'UI).
2. Pas d'auto-save (Ctrl+S ou sauvegarde automatique).
3. README obsolète (décrit l'ancien double-clic pour connecter ; pas de mention drag&drop/lock/WebP/presse-papiers/zoom).
4. **NOTÉ (demande utilisateur, ne pas implémenter tout de suite)** : **Alt+clic sur un carré nouvellement créé → ouvrir directement le renommage**. Ne le faire qu'à la tâche dédiée.

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
