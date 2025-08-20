#!/usr/bin/env python3
"""
Generador de portal estático tipo galería.

Lee un CSV de entrada (texto plano) con las columnas:
    title,url,image,description

- title:        Título de la tarjeta
- url:          URL de destino al hacer clic
- image:        (Opcional) Ruta local a PNG/JPG o URL de imagen. 
                Si está vacío y se pasa --take-screenshots, el script tomará un
                screenshot de la página automáticamente (requiere Playwright).
- description:  Breve descripción que aparece debajo del título.

Salida:
- Carpeta de salida (por defecto ./portal) con:
    - index.html (sitio estático con HTML+CSS+JS)
    - /assets (imágenes y screenshots)

Requisitos opcionales para screenshots:
    pip install playwright
    playwright install chromium

Uso:
    python generate_portal.py --input sites.csv \
        --output-dir portal \
        --title "Mi Portal" \
        --description "Accesos directos con vista previa" \
        --take-screenshots

También puedes generar un CSV de ejemplo:
    python generate_portal.py --make-sample sites.csv
"""
from __future__ import annotations
import argparse
import csv
import os
import re
import sys
import time
import shutil
import textwrap
from pathlib import Path
from urllib.parse import urlparse

try:
    # Usado para placeholders si no hay imagen ni screenshot
    from PIL import Image, ImageDraw, ImageFont  # type: ignore
    PIL_AVAILABLE = True
except Exception:
    PIL_AVAILABLE = False

# Playwright es opcional (solo si se piden screenshots)
PLAYWRIGHT_AVAILABLE = False
try:
    from playwright.sync_api import sync_playwright  # type: ignore
    PLAYWRIGHT_AVAILABLE = True
except Exception:
    PLAYWRIGHT_AVAILABLE = False


def slugify(value: str, allow_unicode: bool = False) -> str:
    value = str(value)
    if allow_unicode:
        value = re.sub(r"\s+", "-", value)
    else:
        value = re.sub(r"[\s_]+", "-", value)
        value = re.sub(r"[^\w\-]", "", value)
    value = re.sub(r"-+", "-", value).strip("-_")
    return value.lower() or "item"


def ensure_dir(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)


def is_url(s: str) -> bool:
    try:
        return urlparse(s).scheme in {"http", "https"}
    except Exception:
        return False


def download_file(url: str, dest: Path) -> None:
    import urllib.request
    with urllib.request.urlopen(url) as r, open(dest, "wb") as f:
        shutil.copyfileobj(r, f)


def read_csv_rows(csv_path: Path) -> list[dict]:
    rows: list[dict] = []
    with open(csv_path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        required = {"title", "url", "image", "description"}
        missing = required - set(h.strip() for h in reader.fieldnames or [])
        if missing:
            raise SystemExit(f"El CSV requiere encabezados: {sorted(required)}. Faltan: {sorted(missing)}")
        for i, row in enumerate(reader, start=2):
            # Normaliza claves
            row = {k.strip(): (v or "").strip() for k, v in row.items()}
            if not row.get("title") or not row.get("url"):
                print(f"[ADVERTENCIA] Fila {i}: 'title' y 'url' son obligatorios. Se omite.")
                continue
            rows.append(row)
    return rows


def make_placeholder(text: str, out_path: Path, size=(1280, 800)) -> None:
    if not PIL_AVAILABLE:
        return
    img = Image.new("RGB", size, (245, 245, 245))
    draw = ImageDraw.Draw(img)
    # Intento cargar una fuente, de lo contrario fuente por defecto
    try:
        font = ImageFont.truetype("arial.ttf", 48)
    except Exception:
        font = ImageFont.load_default()
    wrapped = textwrap.fill(text, width=24)
    #w, h = draw.multiline_textsize(wrapped, font=font)
    bbox = draw.multiline_textbbox((0, 0), wrapped, font=font, align="center")
    w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw.multiline_text(((size[0]-w)//2, (size[1]-h)//2), wrapped, fill=(20, 20, 20), font=font, align="center")
    img.save(out_path)


def take_screenshot(url: str, out_path: Path, timeout_ms: int = 20000, full_page: bool = False) -> bool:
    if not PLAYWRIGHT_AVAILABLE:
        return False
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(viewport={"width": 1280, "height": 800})
            page = context.new_page()
            page.set_default_timeout(timeout_ms)
            page.goto(url, wait_until="networkidle")
            time.sleep(0.8)  # pequeño respiro para fuentes/animaciones
            page.screenshot(path=str(out_path), full_page=full_page)
            context.close()
            browser.close()
        return True
    except Exception as e:
        print(f"[ERROR] Screenshot falló para {url}: {e}")
        return False


def prepare_image(asset_dir: Path, title: str, url: str, image_field: str, take_shots: bool) -> str:
    """Devuelve la ruta relativa al asset generado/copied para usar en HTML."""
    ensure_dir(asset_dir)
    base = slugify(title)[:40]
    ext = ".png"
    target = asset_dir / f"{base}{ext}"

    if image_field:
        if is_url(image_field):
            try:
                download_file(image_field, target)
                return f"assets/{target.name}"
            except Exception as e:
                print(f"[ADVERTENCIA] No se pudo descargar imagen para '{title}': {e}")
        else:
            src = Path(image_field)
            if src.exists():
                shutil.copy2(src, target)
                return f"assets/{target.name}"
            else:
                print(f"[ADVERTENCIA] Imagen no encontrada '{image_field}' para '{title}'.")

    if take_shots:
        ok = take_screenshot(url, target)
        if ok:
            return f"assets/{target.name}"
        else:
            print(f"[ADVERTENCIA] Screenshot no disponible para '{title}'.")

    # Fallback placeholder si PIL está disponible; si no, devolverá una ruta vacía
    if PIL_AVAILABLE:
        make_placeholder(title or url, target)
        return f"assets/{target.name}"
    else:
        return ""


def build_html(items: list[dict], portal_title: str, portal_desc: str) -> str:
    # Tailwind vía CDN para diseño rápido + un poco de JS para búsqueda/tema y animaciones
    # Nota: Todo es estático; no requiere servidores.
    html = f"""<!DOCTYPE html>
<html lang=\"es\">
<head>
  <meta charset=\"utf-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
  <title>{portal_title}</title>
  <link rel=\"preconnect\" href=\"https://fonts.googleapis.com\"> 
  <link rel=\"preconnect\" href=\"https://fonts.gstatic.com\" crossorigin>
  <link href=\"https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap\" rel=\"stylesheet\">
  <script src=\"https://cdn.tailwindcss.com\"></script>
<style>
    :root {{ --card-r: 18px; }}
    html {{ font-family: Inter, system-ui, -apple-system, Segoe UI, Roboto, Arial, sans-serif; }}
    .card:hover img {{ transform: scale(1.04); }}
    .card img {{ transition: transform .25s ease; }}
    .shine {{ position: relative; overflow: hidden; }}
    .shine::after {{
      content: \"\"; position: absolute; top:0; left:-150%; width: 50%; height: 100%;
      background: linear-gradient(120deg, transparent, rgba(255,255,255,.25), transparent);
      transform: skewX(-20deg);
    }}
    .card:hover .shine::after {{ left: 150%; transition: left .75s ease; }}
</style>
</head>
<body class=\"bg-slate-50 text-slate-900 dark:bg-slate-900 dark:text-slate-100 min-h-screen\">
  <div class=\"max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8\">
    <header class=\"flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between\">
      <div>
        <h1 class=\"text-3xl sm:text-4xl font-extrabold\">{portal_title}</h1>
        <p class=\"mt-1 text-slate-600 dark:text-slate-300\">{portal_desc}</p>
      </div>
      <div class=\"flex items-center gap-3 mt-2\">
        <input id=\"search\" type=\"search\" placeholder=\"Buscar...\" class=\"w-64 rounded-xl border border-slate-300 dark:border-slate-700 bg-white/80 dark:bg-slate-800/60 px-3 py-2 outline-none focus:ring-2 focus:ring-indigo-400\" />
        <button id=\"themeToggle\" class=\"rounded-xl px-3 py-2 border border-slate-300 dark:border-slate-700\">Tema</button>
      </div>
    </header>

    <main class=\"mt-6\">
      <div id=\"grid\" class=\"grid gap-6 grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4\">
        {''.join(render_card(i) for i in items)}
      </div>
    </main>

    <footer class=\"text-center text-sm text-slate-500 mt-10\">Generado automáticamente — {time.strftime('%Y-%m-%d')}</footer>
  </div>

  <script>
    // Búsqueda en vivo
    const q = document.getElementById('search');
    const cards = Array.from(document.querySelectorAll('.card'));
    q.addEventListener('input', () => {{
      const v = q.value.toLowerCase();
      cards.forEach(c => {{
        const hay = c.dataset.title.includes(v) || c.dataset.desc.includes(v) || c.dataset.url.includes(v);
        c.style.display = hay ? '' : 'none';
      }});
    }});

    // Tema claro/oscuro
    const toggle = document.getElementById('themeToggle');
    const pref = localStorage.getItem('theme') || (matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');
    document.documentElement.classList.toggle('dark', pref==='dark');
    toggle.addEventListener('click', () => {{
      const now = document.documentElement.classList.toggle('dark');
      localStorage.setItem('theme', now ? 'dark' : 'light');
    }});

    // Abrir en nueva pestaña al pulsar Enter sobre tarjeta enfocada
    document.addEventListener('keydown', (e) => {{
      if (e.key === 'Enter' && document.activeElement?.classList.contains('card')) {{
        const url = document.activeElement.getAttribute('data-href');
        if (url) window.open(url, '_blank');
      }}
    }});
  </script>
</body>
</html>
"""
    return html


def render_card(item: dict) -> str:
    title = item.get("title", "").strip()
    desc = item.get("description", "").strip()
    url = item.get("url", "").strip()
    img = item.get("image_final", "").strip()
    title_html = (title or url).replace('"', '&quot;')
    desc_html = desc.replace('"', '&quot;')
    url_html = url.replace('"', '&quot;')

    img_tag = f'<img src="{img}" alt="{title_html}" class="w-full h-44 object-cover rounded-t-2xl" loading="lazy">' if img else '<div class="w-full h-44 bg-slate-200 dark:bg-slate-700 rounded-t-2xl"></div>'

    return f"""
      <article tabindex=\"0\" class=\"card group rounded-2xl overflow-hidden bg-white/70 dark:bg-slate-800/70 border border-slate-200 dark:border-slate-700 shadow-sm focus:ring-2 focus:ring-indigo-400\" 
               data-title=\"{title_html.lower()}\" data-desc=\"{desc_html.lower()}\" data-url=\"{url_html.lower()}\" data-href=\"{url_html}\">
        <a href=\"{url_html}\" target=\"_blank\" class=\"block shine\">{img_tag}</a>
        <div class=\"p-4\">
          <h3 class=\"font-semibold text-lg leading-tight line-clamp-2\">{title_html}</h3>
          <p class=\"text-sm text-slate-600 dark:text-slate-300 mt-1 line-clamp-3\">{desc_html}</p>
          <div class=\"mt-3 text-xs text-slate-500 truncate\">{url_html}</div>
        </div>
      </article>
    """


def write_site(output_dir: Path, items: list[dict], title: str, desc: str) -> None:
    html = build_html(items, title, desc)
    (output_dir / "index.html").write_text(html, encoding="utf-8")


def make_sample(csv_path: Path) -> None:
    if csv_path.exists():
        print(f"[INFO] Ya existe {csv_path}, no se sobrescribe.")
        return
    rows = [
        {"title": "Gmail", "url": "https://gmail.com", "image": "", "description": "Correo web"},
        {"title": "Wikipedia", "url": "https://wikipedia.org", "image": "", "description": "Enciclopedia libre"},
        {"title": "YouTube", "url": "https://youtube.com", "image": "", "description": "Videos y streams"},
    ]
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["title", "url", "image", "description"])
        writer.writeheader()
        writer.writerows(rows)
    print(f"[OK] CSV de ejemplo creado en {csv_path}")


def main():
    ap = argparse.ArgumentParser(description="Portales")
    ap.add_argument("--input", dest="input_csv", help="Ruta al CSV de sitios (title,url,image,description)")
    ap.add_argument("--output-dir", default="portal", help="Directorio de salida (default: portal)")
    ap.add_argument("--title", dest="portal_title", default="Mi Portal", help="Título del portal")
    ap.add_argument("--description", dest="portal_desc", default="Accesos directos favoritos", help="Descripción breve del portal")
    ap.add_argument("--take-screenshots", action="store_true", help="Tomar screenshots cuando falte imagen (requiere Playwright)")
    ap.add_argument("--fullpage", action="store_true", help="Screenshots de página completa")
    ap.add_argument("--make-sample", dest="sample_csv", help="Crear un CSV de ejemplo en la ruta dada y salir")
    args = ap.parse_args()

    if args.sample_csv:
        make_sample(Path(args.sample_csv))
        return

    if not args.input_csv:
        ap.error("--input es requerido (o usa --make-sample para crear un CSV de ejemplo)")

    input_csv = Path(args.input_csv)
    if not input_csv.exists():
        raise SystemExit(f"No existe el archivo: {input_csv}")

    out_dir = Path(args.output_dir)
    assets_dir = out_dir / "assets"
    ensure_dir(assets_dir)

    rows = read_csv_rows(input_csv)

    items = []
    for row in rows:
        img_rel = prepare_image(assets_dir, row.get("title", ""), row.get("url", ""), row.get("image", ""), args.take_screenshots)
        row["image_final"] = img_rel
        items.append(row)

    write_site(out_dir, items, args.portal_title, args.portal_desc)

    print(f"\n[OK] Portal generado en: {out_dir.resolve()}")
    print("  - Abre index.html en tu navegador")
    if args.take_screenshots and not PLAYWRIGHT_AVAILABLE:
        print("\n[NOTA] Solicitaste screenshots pero Playwright no está disponible. Instálalo con:\n    pip install playwright\n    playwright install chromium")
    if not PIL_AVAILABLE:
        print("\n[NOTA] Pillow no está disponible. Sin placeholder si falta imagen/screenshot. Instala con: pip install pillow")


if __name__ == "__main__":
    main()

