"""Pronóstico de 7 días desde Open-Meteo (gratis, sin clave)."""
import time

import requests

URL = "https://api.open-meteo.com/v1/forecast"


def pronostico(cfg, dias):
    params = {
        "latitude": cfg["lat"], "longitude": cfg["lon"],
        "daily": "temperature_2m_max,temperature_2m_min,precipitation_probability_max",
        "timezone": cfg["zona_horaria"], "forecast_days": dias,
    }
    ultimo = None
    for intento in range(3):
        try:
            r = requests.get(URL, params=params, timeout=30)
            r.raise_for_status()
            d = r.json()["daily"]
            return [
                {"fecha": f, "hi": float(hi), "lo": float(lo),
                 "r": int(p or 0)}
                for f, hi, lo, p in zip(d["time"], d["temperature_2m_max"],
                                        d["temperature_2m_min"],
                                        d["precipitation_probability_max"])
            ]
        except Exception as ex:  # red, JSON, claves
            ultimo = ex
            time.sleep(3 * (intento + 1))
    raise RuntimeError(f"No se pudo obtener el clima: {ultimo}")
