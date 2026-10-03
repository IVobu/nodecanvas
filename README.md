# NodeCanvas

Application bureau Python/Tkinter pour créer des carrés colorés connectés, organisés en dossiers repliables, avec image de fond personnalisable.

## Fonctionnalités

- **Carrés colorés** : clic droit → "Nouveau carré", couleur et nom modifiables
- **Déplacement** : glisser-déposer les carrés
- **Connexions** : double-clic sur un carré → glisser vers un autre carré
- **Liens au survol** : visibles uniquement quand la souris passe sur un carré connecté
- **Dossiers repliables** : double-clic sur un dossier pour replier/déplier
- **Image de fond** : menu → Fond → Charger image de fond
- **Sauvegarde JSON** : menu → Fichier → Exporter/Importer

## Installation

```bash
pip install -r requirements.txt
```

## Utilisation

```bash
python main.py
```

## Raccourcis

| Action | Méthode |
|---|---|
| Nouveau carré | Clic droit → Nouveau carré |
| Nouveau dossier | Clic droit → Nouveau dossier |
| Déplacer un carré | Glisser-déposer |
| Connecter | Double-clic sur un carré → relâcher sur un autre |
| Replier/déplier un dossier | Double-clic sur le dossier |
| Changer couleur | Clic droit sur un carré → Changer couleur |
| Supprimer | Clic droit sur un carré → Supprimer |

## Structure

```
nodecanvas/
├── main.py              # Point d'entrée
├── models.py            # Classes Square, Link, Folder
├── canvas_widget.py     # Canvas Tkinter custom
├── storage.py           # Export/Import JSON
├── dialogs.py           # Dialogues
└── assets/              # Images de fond
```

## Licence

MIT
