# Nano Banana 2 (Gemini image)

Everyday images. Cheap, fast, strong with reference images. Lite is the
default draft model; full is the quality step-up. **Start here for almost
every image request.**

| Field | Value |
|---|---|
| Model ID | `gemini-3.1-flash-image-preview` (quality) · `gemini-3.1-flash-lite-image` (Lite, drafts) |
| Provider | Google AI Studio (also on fal.ai as fallback) |
| Method | Sync (instant reply) |
| Type | Image |
| API key | `.env` → `GEMINI_API_KEY` |
| Docs | https://ai.google.dev/gemini-api/docs/image-generation |
| Cost | ~$0.034 per 1K image (Lite less) — verify at ai.google.dev/pricing |

## Endpoint

```
POST https://generativelanguage.googleapis.com/v1beta/models/{model-id}:generateContent?key={GEMINI_API_KEY}
```

Key goes **in the URL** — that's Google's auth shape.

## Request format

```json
{
  "contents": [{
    "parts": [
      { "text": "the full production prompt" },
      { "inline_data": { "mime_type": "image/png", "data": "<base64 of ref image>" } }
    ]
  }],
  "generationConfig": { "imageConfig": { "aspectRatio": "16:9" } }
}
```

Reference images (logos, faces, products) go as additional `inline_data`
parts — up to several per request. This model follows refs unusually well;
that's its superpower.

## Response handling

Sync — the reply contains the image directly:
`candidates[0].content.parts[]` → the part with `inlineData.data` is the
base64 image (`inlineData.mimeType` gives the format). Decode and save.
Parts may also include a `text` part (commentary) — ignore it.

## Notes

- If Google AI Studio rejects (quota/region), fall back to fal.ai's hosted
  Gemini image endpoint — search "nano banana" at fal.ai/models and use the
  fal recipe shape (`Authorization: Key`, queue.fal.run).
- Aspect ratios: standard set (1:1, 3:4, 4:3, 9:16, 16:9). 2K/4K output via
  `imageConfig.imageSize` where supported.
- Content rules: no real-person likeness without a provided ref; Google is
  strict on celebrity faces.
