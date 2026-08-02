# iluminame.github.io

## Skill `/generate` — imágenes y video con IA, pagando por uso

Habilidad (skill) para Claude construida siguiendo el **blueprint oficial de
RoboNuggets** del video ["This 1 Claude Skill fully replaces your Higgsfield
Subscription"](https://youtu.be/9C4TRbucmhQ): un solo comando que crea
imágenes y videos, enruta cada pedido al modelo capaz más barato, nunca te
sorprende con la factura, y archiva cada resultado en un solo lugar — en vez
de pagar una suscripción tipo Higgsfield (~US$49/mes ≈ US$0.31–0.34 por
imagen).

### Cómo funciona (el pipeline de 4 pasos del blueprint)

1. **Route** — elige el modelo para el trabajo y el proveedor más barato que
   lo corre, y lee la "receta" de ese modelo (`models/*.md`).
2. **Prep refs** — carga imágenes de referencia reales (logos, caras,
   productos) desde `generations/refs/`. Nunca describe un logo con palabras.
3. **Generate** — llama la API según la receta (sync o async con polling) y
   guarda el archivo plano en `generations/`.
4. **Log** — escribe un JSON al lado de cada archivo (mismo nombre, `.json`)
   con el prompt, modelo, parámetros y costo que lo crearon.

### Los 5 modelos cableados

| Modelo | Para qué | Proveedor |
|---|---|---|
| Nano Banana 2 (y Lite) | Imágenes de todos los días, borradores | Google AI Studio / fal.ai |
| GPT Image 2 | Texto legible en imágenes (posters, packaging) | fal.ai |
| Kling 3.0 | Video por defecto: buen movimiento, precio justo | Kie AI |
| Veo 3.1 | Video premium desde un frame inicial, con audio | Google AI Studio |
| Seedance 2.0 Fast | Animar hasta 9 imágenes de referencia | fal.ai |

Agregar un modelo nuevo = agregar un archivo markdown de receta. Nada más.

### Guardarraíles (los que ahorran plata)

- **Cotiza antes de video**: modelo, duración, resolución y dólares — y espera
  tu "sí" explícito. Una aprobación = una corrida.
- **Borrador barato, final bonito**: itera en el modelo de ~$0.01–0.03 y solo
  el favorito se re-corre en el modelo de calidad.
- **Refs reales, nunca descritas**: el logo va como archivo, no como texto.
- **Una carpeta plana** + log sidecar → la galería y cualquier herramienta
  futura leen tu librería sin configuración.
- Tope mensual en `generations/budget.json` (US$20 por defecto);
  `gallery.py --stats` muestra el gasto por mes y proveedor.

### Bonus: la app "Generations"

`python3 scripts/gallery.py` construye `generations/index.html`: un dashboard
oscuro estilo command-center con todo lo generado — buscador, pestañas
(All / Images / Videos / References), orden por fecha, paginación, panel de
**Styles** (los presets disponibles) y panel de **Models** (los modelos
cableados), muro masonry donde los videos se reproducen al pasar el mouse, y
lightbox con el prompt completo, modelo, costo y botón de copiar. Un solo
archivo, sin servidor. Con `--embed` genera una copia portable con las
imágenes incrustadas — hay una demo en
[`demo/generations-demo.html`](demo/generations-demo.html).

El código está en [`.claude/skills/generate/`](.claude/skills/generate/).

### Instalación en Claude Code

Opción A — solo este proyecto: clona el repo y abre Claude Code dentro; el
skill se detecta solo.

Opción B — todos tus proyectos:

```bash
mkdir -p ~/.claude/skills
cp -r .claude/skills/generate ~/.claude/skills/generate
```

Crea un `.env` (nunca lo subas a git — el `.gitignore` ya lo excluye) con al
menos una clave; con dos (Gemini + Kie o fal) cubres casi todo:

```bash
GEMINI_API_KEY=tu_clave      # aistudio.google.com — Nano Banana 2 y Veo 3.1
KIE_API_KEY=tu_clave         # kie.ai — la ruta más barata para modelos populares
FAL_KEY=tu_clave             # fal.ai — primer fallback, mejor documentación
WAVESPEED_API_KEY=tu_clave   # wavespeed.ai — segundo fallback
```

Y en cualquier conversación: `/generate un thumbnail de …`

### Instalación en el chat de Claude (claude.ai)

1. Descarga [`dist/generate.skill`](dist/generate.skill).
2. En claude.ai: **Configuración → Capacidades → Skills → Subir skill**.
3. Pega tu clave API una vez cuando el skill la pida. Si el sandbox no tiene
   internet, el skill te entrega los comandos `curl` listos para tu terminal.

### Costos aproximados (verifica en cada proveedor)

| Trabajo | Precio aprox. |
|---|---|
| Imagen borrador | $0.01–0.03 |
| Imagen de calidad | $0.05–0.15 |
| Video, por segundo | $0.20–0.35 (un clip de 10s = $2–3.50) |

Créditos: blueprint y concepto por Jay E ([RoboNuggets](https://www.youtube.com/@RoboNuggets),
guía completa gratis en skool.com/robonuggets-free). Implementación generada
con Claude a partir del blueprint.
