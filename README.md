# iluminame.github.io

## Skill `/generate` — imágenes y video con IA, pagando por uso

Habilidad (skill) para Claude basada en el video de RoboNuggets
["This 1 Claude Skill fully replaces your Higgsfield Subscription"](https://youtu.be/9C4TRbucmhQ):
en lugar de pagar una suscripción tipo Higgsfield (~US$49/mes, ≈ US$0.31–0.34
por imagen), genera imágenes y videos con IA a través de APIs medidas —
**Kie.ai, fal.ai y WaveSpeed** — pagando solo lo que usas (imagen 2K desde
~US$0.05, clips de video desde ~US$0.10).

Qué hace el skill:

- **Enruta cada pedido al mejor modelo por costo** (Nano Banana, Seedream,
  FLUX, Seedance, Kling, Hailuo, Veo 3…) según sea borrador, arte final o video.
- **Muestra el costo estimado ANTES de generar** y respeta un tope mensual
  (`generations/budget.json`).
- **Presets de estilo** (product-hero, ugc-ad, cinematic, thumbnail, orbit…)
  que convierten un pedido corto en un prompt de nivel profesional.
- **Galería local**: todo se descarga a tu disco (los archivos son tuyos) y se
  arma una galería `generations/index.html` con prompt, modelo, costo y fecha,
  más un registro de gastos (`gallery.py --stats`).
- **De una imagen a un sitio web**: toma la mejor imagen generada y construye
  una landing page completa alrededor de ella.

El código del skill está en [`.claude/skills/generate/`](.claude/skills/generate/).

### Instalación en Claude Code

Opción A — solo para este proyecto: clona este repo y abre Claude Code dentro;
el skill se detecta solo desde `.claude/skills/generate/`.

Opción B — disponible en todos tus proyectos:

```bash
mkdir -p ~/.claude/skills
cp -r .claude/skills/generate ~/.claude/skills/generate
```

Luego exporta al menos una clave API (con una alcanza para empezar):

```bash
export KIE_API_KEY="..."        # https://kie.ai — imágenes más baratas
export FAL_KEY="..."            # https://fal.ai — mejor para video
export WAVESPEED_API_KEY="..."  # https://wavespeed.ai — alternativa
```

Y en cualquier conversación escribe, por ejemplo:
`/generate 4 imágenes de anuncio para mi sérum facial, estilo UGC`.

### Instalación en el chat de Claude (claude.ai)

1. Descarga el paquete [`dist/generate.skill`](dist/generate.skill) (o crea el
   zip tú misma comprimiendo la carpeta `generate/`).
2. En claude.ai ve a **Configuración → Capacidades (Capabilities) → Skills →
   Subir skill** y sube el archivo. (Requiere plan con code execution/skills
   habilitados; también puedes subirlo a un Proyecto.)
3. En el chat, pega tu clave API una vez cuando el skill la pida y pide
   normalmente: *"genera un anuncio para…"*.

Nota: si el sandbox del chat no tiene acceso a internet, el skill igualmente
arma el prompt profesional y te entrega los comandos `curl` listos para correr
en tu terminal.

### Costos y seguridad

- Los precios del skill son estimados; verifica en la página de cada proveedor.
- Nunca subas tus claves API a git (el `.gitignore` ya excluye `.env` y
  `generations/`).
- Tope de gasto mensual configurable en `generations/budget.json`
  (US$20 por defecto).

Créditos: concepto del skill por Jay E ([RoboNuggets](https://www.youtube.com/@RoboNuggets)).
Implementación independiente generada con Claude.
