---
name: generate
description: >-
  Generate images and videos via AI model APIs, pay-as-you-go. Use this skill
  whenever the user wants to generate, create, edit, or animate AI images,
  ads, product shots, posters, thumbnails, logos, social creatives, or video
  clips — triggers include "/generate", "generate image", "generate video",
  "create image", "thumbnail", "animate", "genera una imagen", "crea un
  video", "haz un anuncio". Routes every request to the cheapest capable
  model (Nano Banana 2, GPT Image 2, Kling 3.0, Veo 3.1, Seedance 2.0) across
  Kie AI, fal.ai, WaveSpeed, or Google AI Studio, quotes cost before paid
  runs, uses real reference images from a refs folder, files every output
  flat in one generations folder with a sidecar log, and can build a gallery
  wall or turn an image into a landing page.
---

# /generate

One command that makes images and videos, routes every request to the
cheapest capable model, never surprises the user with a bill, and files every
output in one place. Four-step pipeline on every request:

**Route → Prep refs → Generate → Log**

## Step 1 — Route

Pick the model for the job, then the cheapest provider that runs it well.
**Read the model's recipe file in `models/` before every generation** — it has
the endpoint, auth, exact request shape, and response handling.

| Task | Default model | Recipe |
|---|---|---|
| Image (default — drafts, iteration) | Nano Banana 2 Lite | `models/nano-banana-2.md` |
| Image (quality / reference-driven) | Nano Banana 2 | `models/nano-banana-2.md` |
| Image with readable text (signs, posters, packaging, UI) | GPT Image 2 | `models/gpt-image-2.md` |
| Video (default) | Kling 3.0 | `models/kling-3.md` |
| Video (hero quality, from start frame) | Veo 3.1 | `models/veo-3-1.md` |
| Animate reference images (up to 9) | Seedance 2.0 Fast | `models/seedance-2-fast.md` |

Provider routing:
1. Default to the LOWEST COST provider that runs the model well
   (check Kie AI, fal.ai, WaveSpeed AI, Google AI Studio).
2. If the cheapest route lacks the model, fails auth, or errors, fall back to
   the next provider (fal.ai first fallback, WaveSpeed second).
3. Never hide a provider swap. Say which route ran and why.

Models change monthly. On a "model not found" error, open the provider's
model page, copy the id fresh, and update the recipe file — that's the only
maintenance this system needs. Adding a new model = adding one recipe file
(template at the bottom of `references/providers.md`).

## Step 2 — Prep refs

Load real reference images (logos, faces, product shots, style frames) from
`generations/refs/`. **Never describe a logo or face in words** — a described
logo comes back wrong every time: wrong shape, wrong colors, made-up details.
Pass the actual file into the API call. If the needed ref is missing, stop
and ask the user for it.

For style (not identity), expand the user's short brief into a production
prompt using the preset library in `references/styles.md`.

## Step 3 — Generate

Call the API per the recipe. Most image models are sync (result in one
reply); most video models are async: submit → get task id → poll every 5–15
seconds patiently → download the file **immediately** (result URLs often
expire in hours). Run multiple generations one at a time to avoid rate limits.

The bundled scripts implement both patterns for every provider (stdlib-only
Python — no installs):

```bash
python3 scripts/generate_image.py --check-keys   # which API keys are set?

python3 scripts/generate_image.py --provider google --model gemini-3.1-flash-lite-image \
  --prompt "<final prompt>" --aspect 4:5 --project acme --desc hero-draft \
  --cost 0.02 --out generations

python3 scripts/generate_video.py --provider kie --model kling-3.0/video \
  --prompt "<motion prompt>" --duration 5 --aspect 16:9 \
  --ref generations/refs/product.png --project acme --desc orbit \
  --cost 1.50 --out generations
```

`--dry-run` prints the exact request without spending money. `--ref` accepts
local paths (converted/uploaded as the provider requires) and is repeatable.

## Step 4 — Log

After every save, write the sidecar log: a small JSON file next to the media,
**same basename, `.json` extension** (the scripts do this automatically):

```json
{
  "model": "gemini-3.1-flash-lite-image",
  "prompt": "the full text prompt that was sent to the API",
  "refs": ["refs/logo.png"],
  "params": { "aspect": "16:9", "size": "2K" },
  "est_cost_usd": 0.02,
  "created": "2026-07-30T09:41:00Z"
}
```

Same basename plus `.json` is the contract — any future tool (or a plain
folder search) can recover exactly how any file was made.

## Output

- Save every file FLAT into the user's generations folder (default:
  `generations/` in the workspace; if the user names a folder once, keep
  using it consistently — one flat library is what makes galleries and
  dashboards work with zero setup).
- **No subfolders.** Reference images live in `generations/refs/`.
- Naming: `{project}_{description}_{timestamp}.{ext}`

## Rules (the contract)

- **Quote before video.** State model, duration, resolution, and expected
  dollars, then wait for the user's explicit go before any paid video run.
  Quoting alone is not approval. One approval = one run.
- **Draft cheap, finish pretty.** Iterate on the cheap image model
  (~$0.01–0.03). Only when the user picks a favourite does the same prompt
  rerun on a quality model. For images ≲$0.10 total, state the cost and
  proceed; still respect the monthly cap in `generations/budget.json`
  (`gallery.py --stats` shows spend vs. cap; warn at 80%).
- **Real refs, never described.** (Step 2 — this is the rule that saves the
  most disappointment.)
- **One flat folder.** Sorting into subfolders feels tidy but breaks every
  tool that reads the library.
- **One at a time.** Sequential API calls; no parallel paid jobs.
- **Log every prompt.** Sidecar JSON after every save.
- Keys live in `.env` / environment variables (`KIE_API_KEY`, `FAL_KEY`,
  `WAVESPEED_API_KEY`, `GEMINI_API_KEY`) — read them from there, never paste
  into code, never commit them.
- Ballpark costs (verify on pricing pages before relying on them):
  draft image $0.01–0.03 · quality image $0.05–0.15 · video $0.20–0.35
  **per second** (a 10s clip is $2–3.50 — this is why the cost gate exists).

## After generating

- Rebuild the Generations app: `python3 scripts/gallery.py` writes
  `generations/index.html` — a dashboard of everything ever generated:
  search, filter tabs (All/Images/Videos/References), newest/oldest sort,
  pagination, a Styles panel (the preset library) and a Models panel (the
  wired recipes), masonry wall with hover-play videos, and a lightbox with
  full metadata + copy-prompt. `--embed` makes a single portable file with
  the media inlined (good for sharing). Tell the user where it is.
- Offer exactly one natural next step: rerun the favourite on the quality
  model, animate the winning image into a clip, or build a landing page
  around it (`references/website.md`).

## Bundled files

| File | When to use |
|---|---|
| `models/*.md` | Before every generation — the recipe for the chosen model |
| `references/providers.md` | Provider auth shapes, Kie file upload, troubleshooting, new-recipe template |
| `references/styles.md` | Expanding briefs into production prompts (style presets) |
| `references/website.md` | Turning a generated image into a landing page |
| `scripts/generate_image.py` · `scripts/generate_video.py` | All API calls (sync + async, all providers) |
| `scripts/gallery.py` | Rebuild the Generations dashboard app; `--embed` for a portable copy; `--stats` for spend vs. budget |

In Claude.ai chat without network access: build the exact `curl` commands
from the recipe file for the user to run locally (fallback section in
`references/providers.md`), then log the results into the same folder scheme.
