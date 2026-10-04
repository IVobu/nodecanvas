# NodeCanvas

Application de bureau Python/Tkinter pour créer des carrés colorés, les relier entre eux, les organiser en dossiers repliables, avec image de fond, multi-sélection, annulation et réglages persistants.

## Fonctionnalités

- **Carrés colorés** : couleur, nom et taille modifiables, avec images
- **Recadrage des images** : `C` affiche des poignées sur l'image sélectionnée ; tirez un coin puis validez avec `Entrée` ou annulez avec `Échap`. L'application enregistre une copie recadrée dans `assets/`, sans modifier l'original ; `Ctrl+Z` restaure l'image précédente.
- **Multi-sélection** : glisser depuis un espace vide (ou un fond non déplaçable) pour sélectionner une zone ; un fond déverrouillé reste déplaçable quand l'option le permet, `Maj` reste accepté, `Maj`+clic pour ajouter, `Alt`+clic pour retirer
- **Opérations groupées** : déplacer, redimensionner, tourner, recolorer, verrouiller ou supprimer toute une sélection
- **Copier / coller** : `Ctrl+C` puis `Ctrl+Maj+V` duplique les carrés avec leurs liens internes
- **Annulation / rétablissement** : `Ctrl+Z` / `Ctrl+Maj+Z`, profondeur réglable
- **Connexions** : double-clic sur un carré puis clic sur un autre ; les deux gagnent un pas d'opacité, rendu aux extrémités quand le lien est supprimé
- **Liens visibles** : au survol, pour la sélection / le dossier sélectionné, ou tous à la fois
- **Verrouillage global** : verrouillage séparé des couleurs et positions de tous les carrés
- **Dossiers repliables** : double-clic pour replier/déplier
- **Image de fond** : chargé, redimensionné, tourné, verrouillé, ou rendu non cliquable
- **Zoom et panoramique** : molette pour zoomer, bouton du milieu pour déplacer la vue
- **Carrés rapides** : maintenir `1` ou `2` puis clic droit pour créer un carré prédéfini
- **Opacité des carrés** : `+` / `-` pour le carré survolé, `Maj` pour la sélection, `Ctrl` pour tous ; de 10 % à 100 %, pas réglable
- **Opacité par défaut** : configurable dans Réglages, appliquée aux nouveaux carrés et images
- **Sauvegarde JSON** : export / import, avec menu des fichiers récents
- **Reprise au lancement** : restaure automatiquement le projet récent le plus récent encore valide ; si celui-ci est indisponible, essaie les projets précédents
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
| Sélection multiple | Glisser depuis le vide ; `Maj` reste accepté |
| Ajouter / retirer de la sélection | `Maj`+clic / `Alt`+clic |
| Tout sélectionner | `Ctrl+A` |
| Changer la couleur des carrés sélectionnés | Menu Édition → Changer la couleur de la sélection… |
| Déplacer | Glisser-déposer |
| Redimensionner / tourner | Maintenir `R` + glisser une poignée |
| Connecter | Double-clic sur un carré → relâcher sur un autre |
| Déconnecter la sélection | `D` |
| Réinitialiser rotation / miroir | `0` |
| Miroir horizontal / vertical | `H` / `V` |
| Renommer | `F2` |
| Recadrer l'image sélectionnée | `C`, tirer une poignée, `Entrée` pour appliquer (`Échap` annule) |
| Opacité du carré survolé | `+` / `-` (ou pavé, Page Haut / Page Bas) |
| Opacité de la sélection | `Maj` + `+` / `-` |
| Opacité de tous les carrés | `Ctrl` + `+` / `-` |
| Supprimer | `Suppr` |
| Copier / coller des carrés | `Ctrl+C` / `Ctrl+Maj+V` |
| Coller une image | `Ctrl+V` |
| Annuler / rétablir | `Ctrl+Z` / `Ctrl+Maj+Z` |
| Renommer le fond | Double-clic sur le fond |
| Ignorer les éléments verrouillés | `Ctrl+L` |
| Afficher les connexions | Affichage → Afficher les connexions |
| Verrouiller / déverrouiller les couleurs des carrés | Affichage → Verrouiller la couleur des carrés |
| Verrouiller / déverrouiller les positions des carrés | Affichage → Verrouiller la position des carrés |
| Ouvrir le menu d'un carré verrouillé (pour le déverrouiller) | Clic droit |
| Zoom avant / arrière | Molette |
| Zoom 100 % | `Ctrl+0` |
| Panoramique | Bouton du milieu |

## Structure

```
nodecanvas/
├── main.py              # Point d'entrée et menus
├── canvas_widget.py     # Canvas Tkinter, interactions, réglages
├── opacity.py           # Opacité des carrés (installé par main.py)
├── models.py            # Classes Square, Link, Folder
├── storage.py           # Export / import JSON
├── dialogs.py           # Dialogues de saisie
└── assets/              # Créé à l'exécution : images collées (non versionné)
```

## Licence

MIT
