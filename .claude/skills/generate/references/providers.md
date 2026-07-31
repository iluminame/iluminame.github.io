# Providers: APIs, models, and prices

Three metered providers. All prices are **estimates (verify on the pricing page
when precision matters)** — they change often. Links:

- Kie.ai: https://kie.ai — docs: https://docs.kie.ai — pricing shown per model on each model page
- fal.ai: https://fal.ai — docs: https://docs.fal.ai — pricing on each model page at fal.ai/models
- WaveSpeed: https://wavespeed.ai — docs: https://wavespeed.ai/docs

The bundled scripts already implement the submit → poll → download loop for all
three. This file is for understanding the APIs, fixing errors, choosing models,
and producing manual `curl` fallbacks when scripts can't reach the network.

## Contents
1. [Kie.ai API](#kieai)
2. [fal.ai API](#falai)
3. [WaveSpeed API](#wavespeed)
4. [Model cheat sheet with prices](#model-cheat-sheet)
5. [Finding current model IDs](#finding-current-model-ids)
6. [Manual curl fallback (chat without network)](#manual-curl-fallback)
7. [Troubleshooting](#troubleshooting)

---

## Kie.ai

One API for 300+ models (Nano Banana, Seedream, Flux, Veo, Kling, Sora,
Suno, ElevenLabs…). Auth: `Authorization: Bearer $KIE_API_KEY`.

**Submit** — `POST https://api.kie.ai/api/v1/jobs/createTask`

```json
{
  "model": "google/nano-banana-pro",
  "input": {
    "prompt": "…",
    "aspect_ratio": "4:5",
    "resolution": "2K",
    "image_urls": ["https://…"]   // only for edit/image-to-image models
  }
}
```

Response: `{"code": 200, "data": {"taskId": "…"}}` (any other `code` = error,
message in `msg`).

**Poll** — `GET https://api.kie.ai/api/v1/jobs/recordInfo?taskId=<id>`
`data.state` goes `waiting → queuing → generating → success | fail`.
On success, `data.resultJson` is a JSON *string*; parse it → `resultUrls: [...]`.
On fail, read `data.failMsg`.

Notes: input field names vary slightly per model (check the model's page on
kie.ai, each has an API tab with the exact schema). Images: `image_urls` must be
public URLs — for local files, upload somewhere reachable first or switch to
fal.ai which accepts base64 data URIs.

## fal.ai

Queue-based API, very reliable for long video jobs. Auth: `Authorization: Key $FAL_KEY`.

**Submit** — `POST https://queue.fal.run/<model-id>` (e.g.
`https://queue.fal.run/fal-ai/flux/dev`)

```json
{ "prompt": "…", "image_size": "portrait_4_3", "num_images": 4 }
```

Response: `{"request_id": "…", "status_url": "…", "response_url": "…"}`.

**Poll** — `GET <status_url>` until `"status": "COMPLETED"`, then
`GET <response_url>` → result. Images arrive as `images: [{url, …}]`, video as
`video: {url}`. Input schema differs per model (video models take `duration`,
`aspect_ratio`, `resolution`; image-to-video takes `image_url`) — each model
page at fal.ai/models documents its schema and shows the price.

Notes: `image_url` accepts public URLs **or** `data:` base64 URIs (handy for
local files). Fast image models also work synchronously via
`POST https://fal.run/<model-id>` but the queue endpoint works for everything —
the scripts always use the queue.

## WaveSpeed

Alternative provider covering ByteDance (Seedream/Seedance), Kling, WAN, Flux.
Auth: `Authorization: Bearer $WAVESPEED_API_KEY`.

**Submit** — `POST https://api.wavespeed.ai/api/v3/<model-path>` (e.g.
`bytedance/seedream-v4`), body: `{"prompt": "…", "size": "2048*2048"}`.
Response: `{"code": 200, "data": {"id": "…"}}`.

**Poll** — `GET https://api.wavespeed.ai/api/v3/predictions/<id>/result`
until `data.status` is `completed` → outputs in `data.outputs: [url, …]`.

---

## Model cheat sheet

Approximate prices (mid-2026 — **verify before quoting to the user**).
Comparison anchor: Higgsfield ≈ $49/mo entry plan ≈ $0.31–$0.34 per image.

### Images

| Model | ID (provider) | ~Price | Use for |
|---|---|---|---|
| Nano Banana | `google/nano-banana` (Kie) | $0.02 | Drafts, iterations, volume |
| Nano Banana Pro 2K | `google/nano-banana-pro` (Kie) | $0.05 | **Default final** — text rendering, ads |
| Nano Banana edit | `google/nano-banana-edit` (Kie) | $0.02–0.04 | Image editing/remix by prompt |
| Seedream 4.0 | `bytedance/seedream-v4` (Kie/WaveSpeed) · `fal-ai/bytedance/seedream/v4/text-to-image` (fal) | $0.03 | Photoreal, 4K capable |
| FLUX schnell | `fal-ai/flux/schnell` (fal) | <$0.01 | Instant drafts |
| FLUX dev | `fal-ai/flux/dev` (fal) | $0.03 | Quality general-purpose |
| FLUX 1.1 pro | `fal-ai/flux-pro/v1.1` (fal) | $0.04–0.06 | Hero images |

### Video (per ~5s clip unless noted)

| Model | ID (provider) | ~Price | Use for |
|---|---|---|---|
| WAN 2.2 | `fal-ai/wan/v2.2-a14b/text-to-video` (fal) | $0.08–0.15 | Cheapest motion tests |
| Seedance 1.0 lite | `fal-ai/bytedance/seedance/v1/lite/text-to-video` (fal) | $0.10–0.20 | **Default budget video** |
| Seedance 1.0 pro | `fal-ai/bytedance/seedance/v1/pro/text-to-video` (fal) | $0.40–0.75 | Motion-graphics quality |
| Kling 2.5 turbo pro | `fal-ai/kling-video/v2.5-turbo/pro/text-to-video` · `…/image-to-video` (fal) | $0.35 | **Default standard**, great image→video |
| Hailuo 02 | `fal-ai/minimax/hailuo-02/standard/text-to-video` (fal) | $0.28 | Realistic human motion |
| Veo 3 fast | `google/veo3-fast` (Kie) · `fal-ai/veo3/fast` (fal) | $0.75–1.50 | Premium **with native audio** |
| Veo 3 | `google/veo3` (Kie) · `fal-ai/veo3` (fal) | $3+ | Flagship quality + audio |
| Sora 2 | `sora-2-text-to-video` (Kie) | $0.10–0.15/s | Flagship, availability varies |

Image→video: any `image-to-video` variant of the above; pass the source frame
via `--image-url` (fal accepts local paths — the script converts to base64).

## Finding current model IDs

Model IDs rot. If a call 404s or rejects the model name:
- fal.ai: browse https://fal.ai/models (the URL slug ≈ the model ID) or
  `GET https://fal.ai/api/models?keywords=<term>`.
- Kie.ai: model list + exact input schema per model at https://kie.ai (each
  model page → API tab), or docs.kie.ai "Market" section.
- WaveSpeed: https://wavespeed.ai/models — the model path is in each page's URL.

Update the `--model` argument; don't edit the scripts.

## Manual curl fallback

When running in Claude.ai chat with a sandbox that can't reach the internet,
generate the full commands for the user to paste in their own terminal:

```bash
# 1) Submit (Kie.ai example)
curl -s -X POST https://api.kie.ai/api/v1/jobs/createTask \
  -H "Authorization: Bearer $KIE_API_KEY" -H "Content-Type: application/json" \
  -d '{"model":"google/nano-banana-pro","input":{"prompt":"<PROMPT>","aspect_ratio":"4:5","resolution":"2K"}}'
# 2) Poll (repeat until state=success)
curl -s "https://api.kie.ai/api/v1/jobs/recordInfo?taskId=<TASKID>" \
  -H "Authorization: Bearer $KIE_API_KEY"
# 3) Download each URL from resultJson.resultUrls
curl -o ad-v1.png "<RESULT_URL>"
```

Ask the user to report back the resulting file names/URLs, then log the
generation manually into `generations/log.jsonl` (same fields the scripts write)
so the gallery and cost stats stay accurate.

## Troubleshooting

| Symptom | Likely cause → fix |
|---|---|
| 401 / "Unauthorized" | Wrong or missing env var → `--check-keys`; regenerate key |
| 404 on submit | Model ID changed → [find current ID](#finding-current-model-ids) |
| 402 / "insufficient credits" | Top up the provider account; state remaining spend from `gallery.py --stats` |
| Kie `code != 200` with schema msg | Input field names differ for that model → check its API tab |
| fal stuck `IN_QUEUE` >10 min | Heavy model at peak → keep polling or switch provider/model |
| "content policy" rejection | Rephrase prompt (avoid celebrity/brand/NSFW terms); tell the user why |
| Video URL expires later | Expected — files are already downloaded locally; that's the point |
