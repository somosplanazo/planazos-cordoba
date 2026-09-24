"""Baja eventos de Córdoba desde Qué Hacemos (quehacemos.com.ar).

Buenas prácticas incluidas: respeta robots.txt, se identifica con un User-Agent
propio, hace pausas entre pedidos y nunca reintenta en bucle.
Si la web cambia su HTML, este es el único archivo que hay que ajustar.
"""
import datetime as dt
import json
import re
import time
from urllib import robotparser
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

BASE = "https://www.quehacemos.com.ar"
UA = "PlanazosBot/1.0 (agenda personal sin fines de lucro)"

MESES = {
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6,
    "julio": 7, "agosto": 8, "septiembre": 9, "setiembre": 9, "octubre": 10,
    "noviembre": 11, "diciembre": 12,
}
MESES_NOMBRE = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
                "agosto", "septiembre", "octubre", "noviembre", "diciembre"]

FECHA_RE = re.compile(
    r"^\s*(\d{1,2}) de ([a-záéíóú]+),? (\d{4})(\s*\+\d+ fechas?)?\s*$", re.I)
HORA_RE = re.compile(r"^\d{1,2}:\d{2}$")
PRECIO_RE = re.compile(r"^\$\s*([\d\.,]+)")
CATS_SITIO = {"recital", "teatro", "stand up", "electrónica", "electronica", "fiesta",
              "festival", "deporte", "cuarteto", "arte", "charla", "otro", "infantil",
              "cine", "musical"}
BASURA_DESC = re.compile(
    r"(Este evento requiere|Seleccion[aá] una opci[oó]n|VERIFICACI[OÓ]N DE COMPRA|"
    r"Validaci[oó]n por|Su compra ser[aá]|No hay medios de pago)", re.I)


def parse_precio(texto):
    m = PRECIO_RE.match(texto or "")
    if not m:
        return None
    s = m.group(1).replace(".", "").replace(",", ".")
    try:
        return int(round(float(s)))
    except ValueError:
        return None


def limpiar_desc(desc):
    desc = BASURA_DESC.split(desc)[0]
    desc = re.sub(r"\s+", " ", desc).strip()
    return desc


def parse_ancla(a):
    """Convierte un <a href='/eventos/...'> de la lista en un dict, o None."""
    href = a.get("href", "")
    if "/eventos/" not in href:
        return None
    partes = [p.strip() for p in a.stripped_strings if p.strip()]
    if len(partes) < 3:
        return None

    di = None
    for i, p in enumerate(partes):
        if FECHA_RE.match(p):
            di = i
    if di is None:
        return None
    m = FECHA_RE.match(partes[di])
    dia, mes, anio = int(m.group(1)), MESES.get(m.group(2).lower()), int(m.group(3))
    if not mes:
        return None
    fecha = dt.date(anio, mes, dia)

    ci = next((i for i, p in enumerate(partes[:di]) if p.lower() in CATS_SITIO), None)
    cat_sitio = partes[ci].lower() if ci is not None else ""
    idx = (ci + 1) if ci is not None else 0
    precio = None
    if idx < di and PRECIO_RE.match(partes[idx]):
        precio = parse_precio(partes[idx])
        idx += 1
    if idx >= di:
        return None
    titulo = partes[idx]
    if " en vivo en " in titulo and idx + 1 < di:  # era el alt de la imagen
        idx += 1
        titulo = partes[idx]
    desc = limpiar_desc(" ".join(partes[idx + 1:di]))

    hora, resto = "", []
    for p in partes[di + 1:]:
        if re.match(r"^\+\d+ fechas?$", p, re.I):
            continue
        if HORA_RE.match(p) and not hora:
            hora = p
        else:
            resto.append(p)
    ciudad = resto[0] if resto else ""
    lugar = resto[-1] if resto else ""
    return {
        "url": urljoin(BASE, href), "fecha": fecha.isoformat(), "hora": hora,
        "titulo": titulo, "lugar": lugar, "ciudad": ciudad, "cat_sitio": cat_sitio,
        "precio": precio, "desc": desc,
    }


def parse_jsonld(soup):
    """Ruta preferida si la página trae datos estructurados (schema.org Event)."""
    out = []

    def visitar(x):
        if isinstance(x, list):
            for i in x:
                visitar(i)
        elif isinstance(x, dict):
            t = x.get("@type")
            tipos = t if isinstance(t, list) else [t]
            if any(isinstance(s, str) and s.endswith("Event") for s in tipos):
                out.append(x)
            for v in x.values():
                if isinstance(v, (list, dict)):
                    visitar(v)

    for s in soup.find_all("script", type="application/ld+json"):
        try:
            visitar(json.loads(s.string or ""))
        except (ValueError, TypeError):
            continue
    eventos = []
    for e in out:
        try:
            inicio = str(e.get("startDate", ""))
            fecha = inicio[:10]
            dt.date.fromisoformat(fecha)
            hora = inicio[11:16] if len(inicio) >= 16 else ""
            loc = e.get("location") or {}
            if isinstance(loc, list):
                loc = loc[0] if loc else {}
            addr = loc.get("address") or {}
            ciudad = addr.get("addressLocality", "") if isinstance(addr, dict) else ""
            ofertas = e.get("offers") or {}
            if isinstance(ofertas, list):
                ofertas = ofertas[0] if ofertas else {}
            p = ofertas.get("lowPrice", ofertas.get("price"))
            try:
                precio = int(round(float(p))) if p not in (None, "") else None
            except (TypeError, ValueError):
                precio = None
            eventos.append({
                "url": e.get("url", ""), "fecha": fecha, "hora": hora,
                "titulo": e.get("name", ""), "lugar": loc.get("name", ""),
                "ciudad": ciudad, "cat_sitio": "", "precio": precio,
                "desc": limpiar_desc(e.get("description", "")),
            })
        except (ValueError, AttributeError):
            continue
    return eventos


def parse_pagina(html):
    soup = BeautifulSoup(html, "html.parser")
    por_ancla = []
    for a in soup.find_all("a", href=True):
        ev = parse_ancla(a)
        if ev:
            por_ancla.append(ev)
    if por_ancla:
        return por_ancla
    return parse_jsonld(soup)


def urls_de_fuentes(cfg, hoy):
    sig = (hoy.replace(day=1) + dt.timedelta(days=32)).replace(day=1)
    urls = []
    for f in cfg["fuentes_quehacemos"]:
        u = f.format(mes=MESES_NOMBRE[hoy.month - 1], anio=hoy.year,
                     mes_sig=MESES_NOMBRE[sig.month - 1], anio_sig=sig.year)
        urls.append(urljoin(BASE, u))
    return urls


def bajar(cfg, hoy):
    """Descarga todas las fuentes. Devuelve lista de eventos crudos (sin duplicar por URL)."""
    rp = robotparser.RobotFileParser()
    rp.set_url(urljoin(BASE, "/robots.txt"))
    try:
        rp.read()
    except Exception:
        pass
    ses = requests.Session()
    ses.headers.update({"User-Agent": UA, "Accept-Language": "es-AR,es;q=0.9"})
    vistos, crudos = set(), []
    for url in urls_de_fuentes(cfg, hoy):
        if not rp.can_fetch(UA, url):
            print(f"[robots.txt] no permitido, se omite: {url}")
            continue
        try:
            r = ses.get(url, timeout=30)
        except requests.RequestException as ex:
            print(f"[aviso] no se pudo bajar {url}: {ex}")
            continue
        if r.status_code != 200:
            print(f"[aviso] {url} devolvió {r.status_code}")
            continue
        nuevos = 0
        for ev in parse_pagina(r.text):
            clave = (ev["url"], ev["fecha"])
            if clave in vistos:
                continue
            vistos.add(clave)
            crudos.append(ev)
            nuevos += 1
        print(f"[ok] {url}: {nuevos} eventos nuevos")
        time.sleep(cfg.get("pausa_segundos", 2.0))
    return crudos
