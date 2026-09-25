"""Convierte un evento crudo en un plan con categoría, con quién ir, tipo de lugar, etc.

Todas las reglas están acá para poder ajustarlas fácil.
"""
import difflib
import json
import re
import unicodedata
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data"


def _norm(s):
    s = unicodedata.normalize("NFD", s or "")
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return re.sub(r"\s+", " ", s.lower()).strip()


def cargar_lugares():
    with open(DATA / "venues.json", encoding="utf-8") as f:
        return json.load(f)


def es_centro_cultural(lugar, lugares):
    n = _norm(lugar)
    return any(_norm(x) in n for x in lugares.get("cultural", []))


def kind_de_lugar(lugar, lugares):
    n = _norm(lugar)
    for kind, nombres in lugares.items():
        if any(_norm(x) in n for x in nombres):
            return kind
    return "otro"


def fuera_de_capital(ev, cfg):
    texto = _norm(" ".join([ev.get("titulo", ""), ev.get("lugar", ""), ev.get("ciudad", "")]))
    for palabra in cfg["excluir_palabras"]:
        if re.search(r"\b" + re.escape(_norm(palabra)) + r"\b", texto):
            return True
    return False


def categoria(ev):
    t = _norm(ev["titulo"] + " " + ev.get("desc", ""))
    sitio = ev.get("cat_sitio", "")
    if re.search(r"orquesta|sinfonic|tango|mozart|opera|clasic|camara|carnaval de los animales|falla", t):
        return "clasica"
    if re.search(r"congreso|charla|conferencia|jornada|seminario", t) or sitio == "charla":
        return "charla"
    if re.search(r"feria|\bexpo\b|sexpo", t):
        return "feria"
    if re.search(r"caminata|senderismo|maraton|trail|carrera|running|duatlon|picadas", _norm(ev["titulo"])) \
            or sitio == "deporte":
        return "aire"
    if re.search(r"muestra|exposicion|museo", t) or sitio == "arte":
        return "arte"
    if sitio in {"electronica", "electrónica", "fiesta", "cuarteto"} or \
            re.search(r"techno|\bhouse\b|boliche|fiesta|reggaeton|perreo|cuarteto|\bdj\b", t):
        return "fiesta"
    if sitio in {"stand up", "teatro", "infantil"} or \
            re.search(r"obra|teatro|comedia|danza|improvis|humor|stand up|mentalismo|ecstatic", t):
        return "teatro"
    return "musica"


def con_quien(cat, ev, kind):
    t = _norm(ev["titulo"] + " " + ev.get("desc", ""))
    if cat == "fiesta":
        return "a"
    if cat == "charla":
        return "s"
    if cat == "aire":
        return "saf"
    if re.search(r"\bninos?\b|infantil|familia|todo publico|carnaval de los animales|mozart", t):
        return "f" if cat == "clasica" else "saf"
    if cat in ("arte", "feria"):
        return "saf"
    if cat in ("clasica", "teatro"):
        return "sa"
    if cat == "musica" and (kind == "centro" or "teatro" in _norm(ev.get("lugar", ""))):
        return "sa"
    if re.search(r"jazz|\btrio\b|acustico|intimo|\bcoro\b|piano|cello|violin", t):
        return "sa"
    return "a"


def es_creativo(cat, ev):
    t = _norm(ev["titulo"] + " " + ev.get("desc", ""))
    if cat in ("arte", "teatro") and "stand up" not in t:
        return True
    return bool(re.search(
        r"jazz|\bjam\b|improvis|danza|experiencia|a ciegas|inmersiv|colectiv|folclor|"
        r"world music|instalacion|performance|cello|violonchelo|\bcoro\b|piano", t))


GRATIS_RE = re.compile(
    r"entrada libre|libre y gratuit|entrada gratuit|entrada gratis|actividad libre|entrada sin cargo|gratis hasta", re.I)
HASTA_RE = re.compile(r"gratis hasta (?:las? )?(\d{1,2}[:.]?\d{0,2}) ?(?:hs)?", re.I)


def gratis(ev):
    """Devuelve (True, nota) si el texto dice que la entrada es libre/gratis."""
    d = ev.get("desc", "")
    if not GRATIS_RE.search(d):
        return False, ""
    m = HASTA_RE.search(d)
    if m:
        return True, "GRATIS hasta " + m.group(1).replace(".", ":")
    return True, "entrada libre"


def clave_titulo(t):
    return re.sub(r"[^a-z0-9 ]", "", _norm(t))


def clasificar(ev, cfg, lugares):
    """Devuelve el plan listo para la página, o None si no es de la capital."""
    if fuera_de_capital(ev, cfg):
        return None
    cat = categoria(ev)
    kind = kind_de_lugar(ev["lugar"], lugares)
    hora = ev["hora"] if ev["hora"] not in ("00:00", "0:00") else ""
    vibe = ev.get("desc", "")
    if len(vibe) > 150:
        vibe = vibe[:150].rsplit(" ", 1)[0].rstrip(",;:.") + "…"
    if _norm(vibe).startswith(_norm(ev["titulo"])[:20]) and len(vibe) < 60:
        vibe = ""
    precio, pnote = ev["precio"], ""
    if precio is None:
        es_gratis, nota = gratis(ev)
        if es_gratis:
            precio, pnote = 0, nota
    if cat == "aire":
        kind = "deporte" if re.search(r"maraton|carrera|running|trail|\d+ ?k", _norm(ev["titulo"] + " " + ev.get("desc", ""))) else "afuera"
    return {
        "fecha": ev["fecha"], "time": hora, "title": ev["titulo"],
        "venue": ev["lugar"] or "Lugar a confirmar", "cat": cat, "price": precio,
        "who": con_quien(cat, ev, kind), "vibe": vibe, "kind": kind,
        "cr": es_creativo(cat, ev), "url": ev["url"], "pnote": pnote,
        "freeDays": [], "out": False,
        "unv": (not ev["lugar"]) or ev["lugar"].strip().lower() in ("córdoba", "cordoba"),
        "wh": None, "cultural": es_centro_cultural(ev["lugar"], lugares),
    }


def quitar_duplicados(planes):
    """Mismo día + mismo lugar + títulos muy parecidos = el mismo plan."""
    unicos = []
    for p in planes:
        dup = False
        for q in unicos:
            if q["fecha"] != p["fecha"]:
                continue
            mismo_lugar = _norm(q["venue"]) == _norm(p["venue"])
            parecidos = difflib.SequenceMatcher(
                None, clave_titulo(q["title"]), clave_titulo(p["title"])).ratio() > 0.8
            if parecidos and (mismo_lugar or q["time"] == p["time"]):
                dup = True
                if q["price"] is None and p["price"] is not None:
                    q["price"] = p["price"]
                break
        if not dup:
            unicos.append(p)
    return unicos
