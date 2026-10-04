# NodeCanvas

Application de bureau Python/Tkinter pour créer des carrés colorés, les relier entre eux, les organiser en dossiers repliables, avec image de fond, multi-sélection, annulation et réglages persistants.

## Fonctionnalités

- **Carrés colorés** : couleur, nom et taille modifiables, avec images
- **Multi-sélection** : `Maj`+clic glissé pour une zone de sélection, `Maj`+clic pour ajouter, `Alt`+clic pour retirer
- **Opérations groupées** : déplacer, redimensionner, tourner, recolorer, verrouiller ou supprimer toute une sélection
- **Copier / coller** : `Ctrl+C` puis `Ctrl+Maj+V` duplique les carrés avec leurs liens internes
- **Annulation / rétablissement** : `Ctrl+Z` / `Ctrl+Maj+Z`, profondeur réglable
- **Connexions** : double-clic sur un carré puis clic sur un autre
- **Liens au survol** : visibles seulement au survol d'un carré connecté, couleur et épaisseur réglables
- **Dossiers repliables** : double-clic pour replier/déplier
- **Image de fond** : chargé, redimensionné, tourné, verrouillé, ou rendu non cliquable
- **Zoom et panoramique** : molette pour zoomer, bouton du milieu pour déplacer la vue
- **Carrés rapides** : maintenir `1` ou `2` puis clic droit pour créer un carré prédéfini
- **Sauvegarde JSON** : export / import, avec menu des fichiers récents
- **Réglages persistants** : tout est enregistré dans `~/.nodecanvas_settings.json`

## Installation

Python 3.9 ou plus récent.

```bash
pip install -r requirements.txt
```

Les deux dépendances sont facultatives : sans `Pillow` les images (carrés, fond, presse-papier) sont désactivées, sans `tkinterdnd2` le glisser-déposer de fichiers depuis l'explorateur est indisponible. L'application démarre dans les deux cas.

## Utilisation

```bash
python main.py
```

## Raccourcis

| Action | Méthode |
|---|---|
| Nouveau carré | Clic droit sur le vide → Nouveau carré |
| Carré prédéfini | Maintenir `1` ou `2` + clic droit |
| Nouveau dossier | Clic droit → Nouveau dossier |
| Sélection multiple | `Maj`+clic glissé |
| Ajouter / retirer de la sélection | `Maj`+clic / `Alt`+clic |
| Tout sélectionner | `Ctrl+A` |
| Déplacer | Glisser-déposer |
| Redimensionner / tourner | Maintenir `R` + glisser une poignée |
| Connecter | Double-clic sur un carré → relâcher sur un autre |
| Réinitialiser rotation / miroir | `0` |
| Miroir horizontal / vertical | `H` / `V` |
| Renommer | `F2` |
| Supprimer | `Suppr` |
| Copier / coller des carrés | `Ctrl+C` / `Ctrl+Maj+V` |
| Coller une image | `Ctrl+V` |
| Annuler / rétablir | `Ctrl+Z` / `Ctrl+Maj+Z` |
| Renommer le fond | Double-clic sur le fond |
| Ignorer les éléments verrouillés | `Ctrl+L` |
| Zoom avant / arrière | Molette |
| Zoom 100 % | `Ctrl+0` |
| Panoramique | Bouton du milieu |

## Structure

```
nodecanvas/
├── main.py              # Point d'entrée et menus
├── canvas_widget.py     # Canvas Tkinter, interactions, réglages
├── models.py            # Classes Square, Link, Folder
├── storage.py           # Export / import JSON
├── dialogs.py           # Dialogues de saisie
└── assets/              # Créé à l'exécution : images collées (non versionné)
```

## Licence

MIT
