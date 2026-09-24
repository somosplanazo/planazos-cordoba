"""Arma docs/index.html con eventos + clima.

Uso normal (lo hace GitHub Actions todos los días):   python -m src.build
Prueba sin internet con datos de ejemplo:             python -m src.build --offline --start 2026-09-23
"""
import argparse
import datetime as dt
import json
import sys
from pathlib import Path
from zoneinfo import ZoneInfo

from . import classify, scrape, weather

RAIZ = Path(__file__).resolve().parent.parent
NOMBRES = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
CORTOS = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]
MISIONES = [
    "Lunes sin agenda: escribí 3 planes que nunca hiciste en Córdoba y elegí uno para esta semana.",
    "Martes de museo: el circuito de tres museos sale $2.500. Elegí tu sala favorita y contale a alguien por qué.",
    "Miércoles de museos gratis: elegí UNA obra, mirala 5 minutos y escribí 5 líneas sobre lo que le cambiarías.",
    "Andá a algo que no conocés (una jam, una charla, una banda rara). Anotá 3 palabras que te quedaron dando vueltas.",
    "Sacá 10 fotos camino a tu plan sin filtros. Elegí la mejor y ponele título de libro.",
    "Armá la playlist del finde solo con lo que escuches en vivo. El nombre lo decidís al final.",
    "Domingo de cuaderno: llevalo a donde vayas y dibujá o describí a un desconocido en 3 minutos.",
]


def leer_json(ruta):
    with open(ruta, encoding="utf-8") as f:
        return json.load(f)


def armar_dias(fechas, clima):
    por_fecha = {c["fecha"]: c for c in clima}
    dias = []
    for f in fechas:
        c = por_fecha.get(f.isoformat())
        if c is None:
            raise RuntimeError(f"Falta el clima del {f}")
        dow = f.weekday()
        dias.append({"n": CORTOS[dow], "full": NOMBRES[dow], "d": f.day, "dow": dow,
                     "iso": f.isoformat(), "hi": c["hi"], "lo": c["lo"], "r": c["r"],
                     "m": MISIONES[dow]})
    return dias


def planes_desde_crudos(crudos, cfg, fechas):
    lugares = classify.cargar_lugares()
    idx = {f.isoformat(): i for i, f in enumerate(fechas)}
    planes = []
    for ev in crudos:
        if ev["fecha"] not in idx:
            continue
        p = classify.clasificar(ev, cfg, lugares)
        if p:
            planes.append(p)
    planes = classify.quitar_duplicados(planes)
    for p in planes:
        p["days"] = [idx[p.pop("fecha")]]
    return planes


def planes_desde_extras(fechas):
    out = []
    for x in leer_json(RAIZ / "data" / "extras.json"):
        tope = dt.date.fromisoformat(x["valido_hasta"]) if x.get("valido_hasta") else None
        dias = [i for i, f in enumerate(fechas)
                if f.weekday() in x["dias_semana"] and (tope is None or f <= tope)]
        if not dias:
            continue
        gratis = [i for i in dias if fechas[i].weekday() in x.get("gratis_dia_semana", [])]
        out.append({
            "days": dias, "time": x["hora"], "title": x["titulo"], "venue": x["lugar"],
            "cat": x["cat"], "price": x.get("precio"), "who": x["quien"], "vibe": x["vibe"],
            "kind": x.get("kind", "otro"), "cr": bool(x.get("creativo")), "url": x.get("url", ""),
            "pnote": x.get("nota_precio", ""), "freeDays": gratis, "out": False,
            "unv": bool(x.get("a_confirmar")), "wh": x.get("hora_clima"),
        })
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--offline", action="store_true", help="usa los datos de prueba de tests/")
    ap.add_argument("--start", help="fecha de inicio AAAA-MM-DD (por defecto, hoy)")
    ap.add_argument("--min", type=int, help="mínimo de eventos para publicar")
    ap.add_argument("--out", default=str(RAIZ / "docs" / "index.html"))
    a = ap.parse_args()

    cfg = leer_json(RAIZ / "data" / "config.json")
    tz = ZoneInfo(cfg["zona_horaria"])
    ahora = dt.datetime.now(tz)
    hoy = dt.date.fromisoformat(a.start) if a.start else ahora.date()
    fechas = [hoy + dt.timedelta(days=i) for i in range(cfg["dias"])]

    if a.offline:
        html = (RAIZ / "tests" / "fixture_listing.html").read_text(encoding="utf-8")
        crudos = scrape.parse_pagina(html)
        clima = leer_json(RAIZ / "tests" / "fixture_weather.json")
    else:
        crudos = scrape.bajar(cfg, hoy)
        clima = weather.pronostico(cfg, cfg["dias"])

    dias = armar_dias(fechas, clima)
    planes = planes_desde_crudos(crudos, cfg, fechas)
    minimo = a.min if a.min is not None else cfg["min_eventos"]
    if len(planes) < minimo:
        print(f"ERROR: solo {len(planes)} planes (mínimo {minimo}). No se publica para no pisar "
              "la página buena con una vacía. Revisá src/scrape.py.", file=sys.stderr)
        sys.exit(1)
    planes += planes_desde_extras(fechas)
    for i, p in enumerate(planes):
        p["id"] = i

    datos = {"start": hoy.isoformat(), "days": dias, "events": planes,
             "generated": ahora.strftime("%d/%m/%Y %H:%M")}
    js = json.dumps(datos, ensure_ascii=False).replace("</", "<\\/")
    plantilla = (RAIZ / "template.html").read_text(encoding="utf-8")
    if "/*DATA*/null/*END*/" not in plantilla:
        print("ERROR: la plantilla no tiene el marcador de datos.", file=sys.stderr)
        sys.exit(1)
    salida = plantilla.replace("/*DATA*/null/*END*/", js)
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(salida, encoding="utf-8")
    print(f"Listo: {len(planes)} planes, {len(dias)} días → {a.out}")


if __name__ == "__main__":
    main()
