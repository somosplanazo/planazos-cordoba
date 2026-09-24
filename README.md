# Planazos Córdoba — la agenda que se actualiza sola

Esta carpeta arma cada día una página con los planes de la semana en Córdoba
capital (recitales, museos, fiestas, teatro, ferias, etc.), el clima y
recomendaciones de qué ponerte y cómo llegar. Un robot de GitHub la corre
todos los días a las 8am y publica el resultado en un link fijo, gratis.

No hace falta saber programar para dejarla funcionando: son 10 minutos de
clicks. Después, no tenés que tocar nada más.

## 1. Crear la cuenta y el repositorio

1. Si no tenés, creá una cuenta gratis en **github.com**.
2. Arriba a la derecha, tocá el `+` → **New repository**.
3. Nombre: `planazos-cordoba` (o el que quieras). Dejalo en **Public**
   (necesario para que GitHub Pages sea gratis). Tocá **Create repository**.

## 2. Subir estos archivos

1. En tu repositorio recién creado, tocá **Add file → Upload files**.
2. Arrastrá **todo el contenido** de esta carpeta (`planazos/`), manteniendo
   la estructura de carpetas (`src/`, `data/`, `tests/`, `.github/`, etc.).
   Si el navegador no sube carpetas vacías, no importa — `docs/.gitkeep` ya
   se encarga de que `docs/` exista.
3. Abajo, tocá **Commit changes**.

## 3. Prender GitHub Pages

1. En el repositorio, andá a **Settings → Pages** (menú de la izquierda).
2. En **Source**, elegí **GitHub Actions** (no "Deploy from a branch").
3. Listo, no hay que tocar nada más acá.

## 4. Correrla por primera vez

1. Andá a la pestaña **Actions** del repositorio.
2. A la izquierda, tocá **Actualizar Planazos**.
3. A la derecha, tocá **Run workflow → Run workflow**.
4. Esperá 1-2 minutos y refrescá. Cuando los dos pasos (`build` y `deploy`)
   tengan un tilde verde, tu página ya está online.
5. El link queda en **Settings → Pages**, arriba de todo
   (algo como `https://tu-usuario.github.io/planazos-cordoba/`). Guardalo:
   ese link no cambia nunca, aunque la página se actualice todos los días.

De ahí en más, el robot corre solo todos los días a las 8am (hora de
Córdoba) y republica en el mismo link. No hace falta que abras la compu ni
que le digas nada.

## Cómo está armado (por si algún día lo querés tocar)

- `src/scrape.py` — baja los eventos de Qué Hacemos (quehacemos.com.ar).
  Es la parte más frágil: si ese sitio cambia su diseño, hay que ajustar
  este archivo.
- `src/classify.py` — decide de cada evento: categoría, si es un plan para
  ir sola/con amigos/en familia, si conviene auto o Uber, si "suma
  creatividad", y descarta eventos fuera de la capital.
- `src/weather.py` — trae el pronóstico de 7 días (Open-Meteo, gratis).
- `src/build.py` — junta todo y genera `docs/index.html`, que es la página
  que se publica.
- `data/extras.json` — cosas fijas que no vienen de la web (los museos, la
  feria de Güemes). Podés sumar tus propias entradas ahí, con el mismo
  formato.
- `data/config.json` — ciudad, cuántos días mostrar, y una lista de
  palabras (nombres de otras ciudades) para descartar eventos que no son
  de Córdoba capital.
- Si un día trae **muy pocos eventos** (por ejemplo, porque el sitio de
  origen cambió), la actualización se cancela sola y la página vieja queda
  como estaba, para no reemplazarla por una vacía. Vas a ver el paso
  `build` en rojo en la pestaña Actions: es la señal de que hay que revisar
  `src/scrape.py`.

## Probarlo en tu computadora (opcional, para cuando quieras tocar algo)

```bash
pip install -r requirements.txt
python -m src.build --offline --start 2026-09-23   # con datos de prueba, sin internet
python -m src.build                                 # con datos reales de hoy
python -m pytest tests/ -q                          # corre las pruebas
```

## Una aclaración importante

Los datos de eventos se toman de **Qué Hacemos** (quehacemos.com.ar), un
agregador público de agenda cultural de Córdoba. El robot respeta su
`robots.txt`, se identifica con un nombre propio y espera unos segundos
entre pedido y pedido para no sobrecargar el sitio. Aun así, es un uso no
oficial de sus datos: es para tu agenda personal, no para redistribuirla ni
para un uso comercial. Si en algún momento el sitio cambia sus condiciones
o vos preferís otra fuente, avisame y cambiamos `src/scrape.py`.
