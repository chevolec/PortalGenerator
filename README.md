Aquí tienes un **README.md** optimizado para subirlo a GitHub:

---

```markdown
# Portal Generator

Generador de un portal **estático tipo galería** para tener accesos directos a tus páginas favoritas.  
El portal incluye:
- Tarjetas con **imagen**, título y descripción.
- Si no hay imagen, genera **screenshot automático** (opcional).
- **Modo claro/oscuro** con Tailwind.
- **Buscador en vivo**.
- Diseño responsivo y moderno.

---

## 🚀 Características
✔ Genera un sitio **HTML estático** con **DHTML** (HTML + CSS + JS).  
✔ Usa **TailwindCSS** para un diseño atractivo.  
✔ Cada tarjeta puede usar:
   - Imagen PNG/JPG local
   - URL de imagen
   - **Screenshot automático** con Playwright  
✔ Si no hay imagen y no usas screenshots, genera un **placeholder** con el título.

---

## 📂 Estructura generada
```

portal/
├── index.html
└── assets/
├── img1.png
├── img2.png
└── ...

````

---

## 🛠 Requisitos
- **Python 3.8+**
- Librerías:
  - [Pillow](https://pillow.readthedocs.io/) (para placeholders)
  - [Playwright](https://playwright.dev/python/) (para screenshots automáticos)

Instala dependencias:
```bash
pip install -r requirements.txt
````

Si usarás screenshots:

```bash
playwright install chromium
```

---

## 📄 Archivo CSV de entrada

Debes crear un archivo `sites.csv` con este formato:

```csv
title,url,image,description
ChatGPT,https://chatgpt.com,,Asistente conversacional
Wikipedia,https://wikipedia.org,,Enciclopedia libre
YouTube,https://youtube.com,,Videos y streams
```

* **title**: Título que aparecerá en la tarjeta
* **url**: Enlace al sitio web
* **image**: Ruta a imagen local o URL (opcional)
* **description**: Breve descripción

---

## ▶ Uso básico

Generar un portal con screenshots automáticos:

```bash
python generate_portal.py --input sites.csv --output-dir portal \
  --title "Mi Portal" \
  --description "Accesos directos con vista previa" \
  --take-screenshots
```

Generar un CSV de ejemplo:

```bash
python generate_portal.py --make-sample sites.csv
```

---

## ⚙ Opciones disponibles

```
--input           Ruta al CSV de sitios (requerido)
--output-dir      Carpeta donde se genera el portal (default: portal)
--title           Título del portal
--description     Descripción del portal
--take-screenshots  Toma screenshots si no hay imagen (requiere Playwright)
--fullpage        Screenshots de página completa
--make-sample     Crea un CSV de ejemplo y sale
```

---

## ✨ Ejemplo de resultado

![Ejemplo de galería](docs/demo.png) *(Agrega un screenshot real cuando lo generes)*

---

## 📦 Requisitos para screenshots

Para usar la opción `--take-screenshots`:

```bash
pip install playwright
playwright install chromium
```

---

## ✅ To Do

* [ ] Agregar paginación para muchas tarjetas
* [ ] Soporte para íconos SVG
* [ ] Mejorar estilos hover con animaciones extra


