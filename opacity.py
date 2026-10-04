"""Opacité des carrés pour NodeCanvas — module autonome.

Branché depuis main.py avec `opacity.install(self.canvas)` : le dessin des carrés
reste entièrement dans canvas_widget.py, ce module s'y accroche.

Utilisation
-----------
Touches « + » / « - » (ainsi que « = », le pavé numérique, Page Haut / Page Bas) :

    • carré sous la souris   → ce carré seul
    • Maj + la même touche   → toute la sélection
    • Ctrl + la même touche  → tous les carrés

Menus : Réglages → Opacité…, et clic droit → Opacité (plusieurs entrées).
Menu contextuel et raccourcis ignorent les carrés verrouillés.

Enregistrement
--------------
L'opacité vit dans le modèle (`Square.opacity`, 0 = invisible à 1 = opaque) :
elle est donc écrite dans le JSON du projet — clé « opacity », absente tant que le
carré est opaque, donc les anciens fichiers restent valides — et elle suit
Ctrl+Z / Ctrl+Maj+Z comme n'importe quelle autre propriété.
Le pas de réglage est mémorisé dans ~/.nodecanvas_settings.json.

Rendu
-----
Tkinter ne sait pas transparency les formes : un polygone n'accepte pas de canal
alpha. L'opacité est donc obtenue en mélangeant la couleur du carré avec ce qui
se trouve derrière lui :

    • sans image de fond : mélange avec la couleur du canvas ;
    • avec une image de fond : mélange avec la moyenne des pixels situés sous le
      carré (3 × 3 échantillons), donc le résultat reste juste même si le fond
      est une photo ;
    • carrés-images : l'image est recomposée sur ce fond avec un canal alpha
      réduit (Pillow), en suivant exactement le même chemin que
      `NodeCanvas._photo_for` — ajustement, miroir, rotation.

Sans Pillow, les carrés-images ne sont pas translucides (ils n'ont pas de rendu
translucide possible) mais les carrés unis le sont, car le mélange de couleurs
n'a besoin que de Tk.
"""
import time

from canvas_widget import (PIL_AVAILABLE, RES, TRANSPOSE, Image, ImageTk,
                           _load_settings, _save_settings)
from models import crop_pixel_bounds

MIN_OPACITY = 0.1          # 10 % : en dessous, le carré devient introuvable au clic
MAX_STEP = 0.5
DEFAULT_STEP = 0.10
BURST_SECONDS = 0.35       # deux appuis plus proches = auto-répétition = un seul instantané
INC_KEYS = {"plus", "equal", "KP_Add", "Prior"}       # « + », « = », pavé, Page Haut
DEC_KEYS = {"minus", "KP_Subtract", "Next"}           # « - », pavé, Page Bas
CTRL_MASK, SHIFT_MASK = 0x0004, 0x0001
TEXT_COLOR = "#FFFFFF"     # couleur du nom écrit dans le carré (_draw_square)
SCOPES = {"all": "tous les carrés", "hover": "carré survolé", "selection": "sélection"}


def _clamp(value):
    return max(MIN_OPACITY, min(1.0, round(float(value), 3)))


def _pct(value):
    return f"{round(value * 100)} %"


class OpacityFeature:
    """Applique et pilote l'opacité des carrés d'un NodeCanvas."""

    def __init__(self, canvas):
        self.canvas = canvas
        self.step = self._load_step()
        self.default_opacity = self._load_default_opacity()
        canvas.default_square_opacity = self.default_opacity
        self._colors = {}          # (couleur, opacité, fond) -> couleur mélangée
        self._backdrops = {}       # id carré -> couleur moyenne du fond sous le carré
        self._photos = {}          # id carré -> PhotoImage composé (référence Tk vivante)
        self._photo_keys = {}      # id carré -> clé du cache de composition
        self._signature = None     # état du fond : change -> caches vidés
        self._last_push = 0.0      # dernier instantané d'annulation
        self._stack_depth = len(getattr(canvas, "_undo_stack", []))
        self._bubble_job = None

        self._orig_draw = canvas._draw_square
        canvas._draw_square = self._draw_square
        canvas.bind("<Key>", self._on_key, add="+")
        self._install_context_menu()

    # ------------------------------------------------------------------
    # Dessin
    # ------------------------------------------------------------------
    def _draw_square(self, sq, *args, **kwargs):
        """Enveloppe `NodeCanvas._draw_square` : même dessin, puis opacité."""
        self._orig_draw(sq, *args, **kwargs)
        opacity = getattr(sq, "opacity", 1.0)
        if opacity < 0.999:
            fast = args[0] if args else kwargs.get("fast", False)
            self._apply(sq, opacity, bool(fast))

    def _apply(self, sq, opacity, fast):
        """Assombrit/éclaircit les items déjà dessinés pour ce carré (le code de
        dessin reste intact : pas de nouveau polygon, pas de nouvelle pile)."""
        c = self.canvas
        items = c.find_withtag(c._tag(sq))
        if not items:
            return
        self._refresh_signature()
        backdrop = self._backdrop(sq)
        for item in items:
            kind = c.type(item)
            if kind == "image":
                self._fade_photo(sq, item, opacity, fast, backdrop)
            elif kind in ("polygon", "rectangle"):
                fill = c.itemcget(item, "fill")
                outline = c.itemcget(item, "outline")
                if fill:
                    fill = self._blend(fill, opacity, backdrop)
                if outline:
                    outline = self._blend(outline, opacity, backdrop)
                c.itemconfigure(item, fill=fill, outline=outline)
            elif kind == "text":
                c.itemconfigure(item, fill=self._blend(TEXT_COLOR, opacity, backdrop))

    def _blend(self, color, opacity, backdrop):
        key = (color, opacity, backdrop)
        cached = self._colors.get(key)
        if cached:
            return cached
        rgb = self._to_rgb(color)
        if rgb is None:
            return color
        mixed = "#%02X%02X%02X" % tuple(
            max(0, min(255, round(c * opacity + b * (1 - opacity))))
            for c, b in zip(rgb, backdrop))
        self._colors[key] = mixed
        return mixed

    def _to_rgb(self, color):
        try:
            r, g, b = self.canvas.winfo_rgb(color)
        except Exception:
            return None
        return r >> 8, g >> 8, b >> 8

    # ------------------------------------------------------------------
    # Ce qui se trouve derrière le carré
    # ------------------------------------------------------------------
    def _refresh_signature(self):
        c = self.canvas
        signature = (id(getattr(c, "bg_original", None)),
                     round(getattr(c, "bg_x", 0), 1), round(getattr(c, "bg_y", 0), 1),
                     round(getattr(c, "bg_width", 0), 1), round(getattr(c, "bg_height", 0), 1))
        if signature != self._signature:
            self._signature = signature
            self._colors.clear()
            self._backdrops.clear()
            self._photo_keys.clear()

    def _backdrop(self, sq):
        """Couleur moyenne du fond sous le carré (canvas ou image de fond)."""
        cached = self._backdrops.get(sq.id)
        position = (sq.x, sq.y, sq.size)
        if cached and cached[:3] == position:
            return cached[3]
        c = self.canvas
        base = self._to_rgb(c.cget("bg")) or (45, 45, 45)
        color = base
        img = getattr(c, "bg_original", None)
        if PIL_AVAILABLE and img is not None:
            px, py = getattr(c, "bg_x", 0), getattr(c, "bg_y", 0)
            pw, ph = getattr(c, "bg_width", 0), getattr(c, "bg_height", 0)
            x2, y2 = sq.x + sq.size, sq.y + sq.size
            if pw and ph and sq.x < px + pw and x2 > px and sq.y < py + ph and y2 > py:
                rs = gs = bs = 0
                count = 0
                for i in range(3):
                    for j in range(3):
                        u = self._to_pixel((sq.x + (x2 - sq.x) * (i + 0.5) / 3 - px) / pw * img.width, img.width)
                        v = self._to_pixel((sq.y + (y2 - sq.y) * (j + 0.5) / 3 - py) / ph * img.height, img.height)
                        sample = self._sample(img, u, v, base)
                        if sample:
                            rs, gs, bs, count = rs + sample[0], gs + sample[1], bs + sample[2], count + 1
                if count:
                    color = (rs // count, gs // count, bs // count)
        self._backdrops[sq.id] = position + (color,)
        return color

    @staticmethod
    def _to_pixel(value, size):
        return max(0, min(size - 1, int(value)))

    def _sample(self, img, u, v, base):
        try:
            pixel = img.getpixel((u, v))
        except Exception:
            return None
        if not isinstance(pixel, tuple):        # image en palette : non gérable tel quel
            return None
        if len(pixel) == 4:                     # pixel transparent : on voit le canvas
            a = pixel[3] / 255
            return tuple(round(p * a + b * (1 - a)) for p, b in zip(pixel[:3], base))
        return pixel[0], pixel[1], pixel[2]

    # ------------------------------------------------------------------
    # Carrés-images
    # ------------------------------------------------------------------
    def _fade_photo(self, sq, item, opacity, fast, backdrop):
        c = self.canvas
        if not (PIL_AVAILABLE and sq.image_path):
            return
        src = c._images.get(sq.id)              # déjà chargé par _photo_for
        if src is None:
            return
        photo = self._composite(sq, src, opacity, fast, backdrop)
        if photo is not None:
            self._photos[sq.id] = photo         # sans cette référence, Tk efface l'image
            c.itemconfigure(item, image=photo)

    def _composite(self, sq, src, opacity, fast, backdrop):
        """Rejoue le pipeline de `_photo_for` (ajustement, miroir, rotation) en
        réduisant l'alpha, puis compose sur le fond."""
        c = self.canvas
        box = max(int(sq.size * c.zoom) - 4, 1)
        rot = getattr(sq, "rotation", 0.0) % 360
        fh, fv = getattr(sq, "flip_h", False), getattr(sq, "flip_v", False)
        crop = None if getattr(c, "_crop_square", None) is sq else getattr(sq, "image_crop", None)
        key = (box, fast, round(rot, 2), fh, fv, opacity, backdrop, crop)
        if self._photo_keys.get(sq.id) == key:
            return self._photos.get(sq.id)
        try:
            if crop is not None:
                bounds = crop_pixel_bounds(crop, src.width, src.height)
                src = src.crop((bounds[0], bounds[1], max(bounds[0] + 1, bounds[2]),
                                max(bounds[1] + 1, bounds[3])))
            scale = min(box / src.width, box / src.height)
            size = (max(int(src.width * scale), 1), max(int(src.height * scale), 1))
            base = src.resize(size, RES.BILINEAR if fast else RES.LANCZOS)
            if fh:
                base = base.transpose(TRANSPOSE.FLIP_LEFT_RIGHT)
            if fv:
                base = base.transpose(TRANSPOSE.FLIP_TOP_BOTTOM)
            base.putalpha(base.getchannel("A").point(lambda a: int(a * opacity)))
            out = Image.alpha_composite(Image.new("RGBA", base.size, backdrop + (255,)), base)
            if rot:
                out = out.rotate(-rot, RES.BILINEAR if fast else RES.BICUBIC, expand=True)
            photo = ImageTk.PhotoImage(out)
        except Exception:
            return None
        self._photo_keys[sq.id] = key
        return photo

    # ------------------------------------------------------------------
    # Cibles
    # ------------------------------------------------------------------
    def _targets(self, scope):
        c = self.canvas
        if scope == "all":
            return [s for s in c.squares if not s.locked]
        hovered = c.hovered_square
        if scope == "hover":
            return [] if hovered is None or hovered.locked else [hovered]
        selected = [s for s in c.squares if c._is_selected(s) and not s.locked]
        if selected or hovered is None:
            return selected
        return [] if hovered.locked else [hovered]

    def _snapshot(self):
        """L'auto-répétition d'une touche maintenue ne doit pas remplir
        l'historique : seul le premier appui de la rafale pousse un instantané.

        Le délai ne suffit pas — si une autre action (taille, couleur…) a poussé son
        propre instantané entre-temps, il faut bien en créer un nouveau, sinon
        Ctrl+Z annulerait cette action-là et perdrait l'opacité.
        """
        c = self.canvas
        depth = len(c._undo_stack)
        now = time.monotonic()
        if depth != self._stack_depth or now - self._last_push > BURST_SECONDS:
            c.push_undo()
            self._stack_depth = len(c._undo_stack)
            self._last_push = now

    def _commit(self, targets, scope):
        for sq in targets:
            self.canvas._draw_square(sq)
        value = getattr(targets[-1], "opacity", 1.0)
        if len(targets) == 1:
            self._bubble(targets[0], value)
        scope_text = SCOPES.get(scope, scope)
        count = "" if len(targets) == 1 else f", {len(targets)} carré(s)"
        self.canvas._notice(f"Opacité {_pct(value)} ({scope_text}{count})")

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------
    def bump(self, sign=1, scope="selection"):
        targets = self._targets(scope)
        if not targets:
            self.canvas._notice("Aucun carré à modifier")
            return
        self._snapshot()
        for sq in targets:
            sq.opacity = _clamp(getattr(sq, "opacity", 1.0) + sign * self.step)
        self._commit(targets, scope)

    def set_opacity(self, opacity, scope="selection"):
        targets = self._targets(scope)
        if not targets:
            self.canvas._notice("Aucun carré à modifier")
            return
        self._snapshot()
        for sq in targets:
            sq.opacity = _clamp(opacity)
        self._commit(targets, scope)

    def increase_link_opacity(self, squares):
        return self.adjust_link_opacity(squares, 1)

    def decrease_link_opacity(self, squares):
        return self.adjust_link_opacity(squares, -1)

    def adjust_link_opacity(self, squares, direction):
        updated = []
        for sq in squares:
            if sq is None:
                continue
            current = getattr(sq, "opacity", 1.0)
            sq.opacity = _clamp(current + direction * self.step)
            if sq.opacity != current and sq not in updated:
                updated.append(sq)
        for sq in updated:
            self.canvas._draw_square(sq)
        return len(updated)

    def reset(self, scope="selection"):
        self.set_opacity(1.0, scope)

    def ask(self, scope="selection"):
        from tkinter import simpledialog
        targets = self._targets(scope)
        low = round(MIN_OPACITY * 100)
        initial = round(getattr(targets[0], "opacity", 1.0) * 100) if targets else 100
        prompt = (f"Opacité de {initial} % ?" if len(targets) == 1
                  else f"Opacité (de {low} à 100 %) :")
        value = simpledialog.askinteger("Opacité des carrés", prompt,
                                        initialvalue=max(initial, low), minvalue=low, maxvalue=100,
                                        parent=self.canvas.winfo_toplevel())
        if value is not None:
            self.set_opacity(value / 100, scope)

    def ask_step(self):
        from tkinter import simpledialog
        value = simpledialog.askinteger(
            "Pas d'opacité", "Variation à chaque appui (en %, de 1 à 50) :",
            initialvalue=round(self.step * 100), minvalue=1, maxvalue=round(MAX_STEP * 100),
            parent=self.canvas.winfo_toplevel())
        if not value:
            return
        self.step = value / 100
        data = _load_settings()
        data["opacity_step"] = self.step
        _save_settings(data)
        self.canvas._notice(f"Pas d'opacité : {value} %")

    def ask_default_opacity(self):
        from tkinter import simpledialog
        value = simpledialog.askinteger(
            "Opacité des nouveaux carrés", "Opacité (de 10 à 100 %) :",
            initialvalue=round(self.default_opacity * 100), minvalue=10, maxvalue=100,
            parent=self.canvas.winfo_toplevel())
        if value is None:
            return
        self.default_opacity = value / 100
        self.canvas.default_square_opacity = self.default_opacity
        data = _load_settings()
        data["default_square_opacity"] = self.default_opacity
        _save_settings(data)
        self.canvas._notice(f"Opacité des nouveaux carrés : {value} %")

    # ------------------------------------------------------------------
    # Raccourcis
    # ------------------------------------------------------------------
    def _on_key(self, event):
        if event.keysym in INC_KEYS:
            sign = 1
        elif event.keysym in DEC_KEYS:
            sign = -1
        else:
            return None
        state = event.state
        if state & CTRL_MASK:
            scope = "all"
        elif state & SHIFT_MASK:
            scope = "selection"
        elif self.canvas.hovered_square is not None:
            scope = "hover"
        else:
            scope = "selection"
        self.bump(sign, scope)
        return "break"

    def _bubble(self, sq, opacity):
        """Petit pourcentage affiché au-dessus du carré modifié."""
        c = self.canvas
        z = c.zoom
        cx, cy = sq.center()
        c.delete("opa_bubble")
        c.create_text(cx * z, cy * z - sq.size * z / 2 - 10, text=_pct(opacity),
                      fill=TEXT_COLOR, anchor="s", tags="opa_bubble",
                      font=("Segoe UI", max(round(10 * z), 7), "bold"))
        c.tag_raise("opa_bubble")
        if self._bubble_job:
            c.after_cancel(self._bubble_job)
        self._bubble_job = c.after(900, lambda: c.delete("opa_bubble"))

    # ------------------------------------------------------------------
    # Menus
    # ------------------------------------------------------------------
    def _install_context_menu(self):
        menu = getattr(self.canvas, "context_menu", None)
        if menu is None:
            return
        menu.add_separator()
        menu.add_command(label="Opacité : plus opaque (+)", command=lambda: self.bump(1))
        menu.add_command(label="Opacité : plus transparent (-)", command=lambda: self.bump(-1))
        menu.add_command(label="Opacité… (sélection)", command=self.ask)
        menu.add_command(label="Opacité 100 % (sélection)", command=lambda: self.reset())

    @staticmethod
    def _load_default_opacity():
        opacity = _load_settings().get("default_square_opacity", 1.0)
        if isinstance(opacity, (int, float)) and MIN_OPACITY <= opacity <= 1.0:
            return float(opacity)
        return 1.0

    def _load_step(self):
        step = _load_settings().get("opacity_step", DEFAULT_STEP)
        if isinstance(step, (int, float)) and 0.01 <= step <= MAX_STEP:
            return float(step)
        return DEFAULT_STEP


def install(canvas):
    """Active l'opacité sur un NodeCanvas et ajoute les commandes de menu."""
    feature = OpacityFeature(canvas)
    canvas.opacity = feature
    canvas.set_opacity_step = feature.ask_step
    canvas.set_default_square_opacity = feature.ask_default_opacity
    canvas.ask_opacity = feature.ask
    canvas.ask_opacity_all = lambda: feature.ask("all")
    canvas.reset_opacity = feature.reset
    return feature
