---
name: generate
description: >-
  Pay-as-you-go AI image and video generation that replaces a Higgsfield-style
  subscription. Use this skill whenever the user wants to generate, create, or
  edit AI images, ads, product shots, posters, thumbnails, logos, social media
  creatives, or AI video clips (cinematic shots, UGC ads, product orbits,
  logo reveals) — including requests like "/generate", "generate an ad",
  "genera una imagen", "crea un video", "haz un anuncio", "make a thumbnail",
  or "animate this image". Routes each request to the best-value model on
  Kie.ai, fal.ai, or WaveSpeed, shows the estimated cost BEFORE generating,
  applies style presets, saves everything to a local gallery with a running
  cost log, and can turn a generated image into a full landing page.
---

# /generate — Pay-as-you-go AI image & video generation

Generate images and videos through metered APIs (Kie.ai, fal.ai, WaveSpeed)
instead of a flat subscription. The philosophy, in order of priority:

1. **Cost transparency.** The user sees the estimated cost of every generation
   *before* it runs. A subscription hides cost per asset; this skill surfaces it.
2. **You own the outputs.** Files are downloaded to the user's disk immediately
   (provider-hosted URLs expire, and platform terms can change — that's the whole
   reason this skill exists). Never leave results only as remote URLs.
3. **Right model for the job.** A $0.02 model is fine for drafts; spend more only
   when the brief demands it. Cheap first, premium on request.

Reference for context: a Higgsfield subscription starts around $49/month and works
out to roughly $0.31–$0.34 per image. The default image model here costs about
$0.05 per 2K image — state this comparison if the user asks "is this cheaper?".

## Setup (first use)

The scripts need at least one provider API key as an environment variable:

| Provider  | Env var             | Get a key at              | Best for |
|-----------|---------------------|---------------------------|----------|
| Kie.ai    | `KIE_API_KEY`       | https://kie.ai            | Cheapest images, huge model catalog |
| fal.ai    | `FAL_KEY`           | https://fal.ai/dashboard  | Video generation, reliable queue |
| WaveSpeed | `WAVESPEED_API_KEY` | https://wavespeed.ai      | Alternative for both |

Check what's available with: `python3 scripts/generate_image.py --check-keys`

- **Claude Code:** the user can export the key in their shell profile or a `.env`
  file (never commit it — check `.gitignore` covers it).
- **Claude.ai chat:** ask the user to paste the key once, export it inside the
  code-execution sandbox for the session. If the sandbox blocks outbound network
  calls, fall back to *manual mode*: build the exact `curl` commands and JSON
  payloads (see `references/providers.md`) and hand them to the user to run
  locally, then continue the workflow with the files they report back.

If no key exists yet, don't stall: help the user pick ONE provider (default:
Kie.ai for images, fal.ai if they mainly want video), link the signup page, and
continue once they have a key. Most providers give free starter credits.

## The workflow

Follow these steps for every generation request:

### 1. Understand the brief
Extract: subject, purpose (ad? thumbnail? hero image? clip?), aspect ratio,
how many variations, and any style cues. Don't interrogate the user — infer
sensible defaults (ads → 1:1 or 4:5, thumbnails → 16:9, stories → 9:16,
video → 16:9, 5s) and state them.

### 2. Apply a style preset
Read `references/styles.md` and pick the preset that matches the brief (or
combine two). Expand the user's short request into a full production prompt
using the preset's scaffold: subject → action → setting → lighting → camera →
mood → on-image text. Show the user the final prompt. A well-built prompt is
what makes a $0.05 model look like a $49/month platform.

### 3. Route to a model
Default routing (details, exact model IDs, and API shapes in
`references/providers.md` — read it before the first generation of a session):

| Task | Default | Step up | Premium |
|------|---------|---------|---------|
| Image (draft/iteration) | Kie.ai · nano-banana (~$0.02) | — | — |
| Image (final, 2K) | Kie.ai · nano-banana-pro (~$0.05) | fal.ai · FLUX dev (~$0.03) | fal.ai · FLUX pro (~$0.05+) |
| Image edit / remix (image→image) | Kie.ai · nano-banana edit | fal.ai · seedream v4 edit | — |
| Video 5s (budget) | fal.ai · Seedance lite / WAN (~$0.10–0.20) | — | — |
| Video 5s (standard) | fal.ai · Kling 2.5 turbo (~$0.35) | fal.ai · Hailuo-02 | — |
| Video with audio / flagship | — | — | Veo 3 fast (~$1.20) / Veo 3 (~$3+) |

Rules of thumb: iterate cheap, upscale/premium only the winning variant; prefer
the provider the user already has a key for; batch variations in one call when
the API supports `num_images`.

### 4. Estimate cost and confirm
Always print the estimate before generating:
`→ 4 images · nano-banana-pro · ~$0.20 total`.
- Total ≤ $0.50 and within any stated budget → proceed without asking.
- Total > $0.50, or premium video models, or the monthly cap in
  `generations/budget.json` would be crossed → ask the user first.
- After each run, the cost log accumulates in `generations/log.jsonl`;
  `python3 scripts/gallery.py --stats` shows spend vs. cap.

### 5. Generate
Use the bundled scripts (stdlib-only Python, no installs needed):

```bash
# Images
python3 scripts/generate_image.py --provider kie --model google/nano-banana-pro \
  --prompt "<final prompt>" --aspect 4:5 --count 4 --cost 0.05 --out generations

# Video (submits, polls, downloads — video jobs can take 1–6 min)
python3 scripts/generate_video.py --provider fal --model fal-ai/bytedance/seedance/v1/lite/text-to-video \
  --prompt "<final prompt>" --duration 5 --aspect 16:9 --cost 0.15 --out generations

# Image → video (animate a generated image)
python3 scripts/generate_video.py --provider fal --model fal-ai/kling-video/v2.5-turbo/pro/image-to-video \
  --prompt "<camera + motion prompt>" --image-url <url-or-path> --cost 0.35 --out generations
```

Add `--dry-run` to print the exact API request without spending money — use it
when debugging or when the user just wants to see what would happen. If a script
fails with an API error, read the error body: most failures are a wrong model ID
(check `references/providers.md` → "Finding current model IDs") or a missing key.

### 6. Update the gallery
Every successful run already appends to `generations/log.jsonl`. Rebuild the
browsable gallery and show totals:

```bash
python3 scripts/gallery.py            # writes generations/index.html
python3 scripts/gallery.py --stats    # spend by month/provider vs budget cap
```

Tell the user where their files are and open/link `generations/index.html`.
The gallery shows every asset with its prompt, model, cost, and date — this is
the user's owned, local replacement for a platform's cloud gallery.

### 7. Offer the natural next step
Based on what was generated, offer exactly one relevant follow-up:
- Draft images → "want me to upscale / re-run the best one at 2K?"
- Final image → "want me to animate this into a 5s clip?" (image→video)
- A strong hero image → "want me to build a landing page around it?" —
  then follow `references/website.md` (image → full website workflow).

## Guardrails

- Never expose or print API keys; never commit them (keep `.env` and
  `generations/` out of git unless the user explicitly wants outputs versioned).
- Respect `generations/budget.json` (`{"monthly_cap_usd": 20}` by default —
  create it on first run if missing). Warn at 80% of cap.
- Prices in this skill are estimates; when the user needs exact numbers, check
  the provider's pricing page (links in `references/providers.md`).
- Don't generate content that violates provider ToS (real-person deepfakes,
  trademarked characters for commercial use, etc.) — flag it and offer an
  alternative concept instead.

## Bundled files

| File | When to read/use |
|------|------------------|
| `references/providers.md` | Before the first generation of a session: API endpoints, auth, model IDs, prices, curl fallbacks, error fixes |
| `references/styles.md` | Step 2 of every request: style presets and the prompt formula |
| `references/website.md` | When turning a generated image into a landing page |
| `scripts/generate_image.py` | All image generation/editing calls |
| `scripts/generate_video.py` | All video generation calls (text→video and image→video) |
| `scripts/gallery.py` | After generations, and for `--stats` cost reports |
