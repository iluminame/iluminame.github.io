# Seedance 2.0 Fast (reference-to-video)

Reference to video: feed it up to 9 images and it animates them. The pick
when you want to animate real reference images (product angles, brand
frames, a character sheet) rather than a text prompt.

| Field | Value |
|---|---|
| Model ID | `bytedance/seedance-2.0/fast/reference-to-video` |
| Provider | fal.ai |
| Method | Sync-ish via queue (one call through the queue API; fast) |
| Type | Video |
| API key | `.env` → `FAL_KEY` |
| Docs | https://fal.ai/models/bytedance/seedance-2.0/fast/reference-to-video |
| Cost | ~$0.24 per second at 720p → a 5-second clip ≈ $1.21 — verify on the model page |

## Endpoint

```
POST https://queue.fal.run/bytedance/seedance-2.0/fast/reference-to-video
```

Auth header uses the word **Key**: `Authorization: Key {FAL_KEY}`.

## Request format

```json
{
  "prompt": "the products assemble into a flat-lay, camera slowly orbits",
  "image_urls": ["<ref 1>", "<ref 2>", "…up to 9"],
  "duration": 5,
  "resolution": "720p",
  "aspect_ratio": "16:9"
}
```

`image_urls` accepts public URLs or `data:` base64 URIs — local files from
`generations/refs/` work directly (the bundled script converts them).

## Response handling

Queue flow: reply has `status_url` + `response_url`; poll `status_url` until
`COMPLETED`, then GET `response_url` → `video.url`. Download immediately.

## Notes

- **Cost gate applies** (≈$1+ per clip): quote duration × $0.24/s and wait
  for the explicit go.
- The refs ARE the content — this model exists so you never describe a logo
  or product in words. Order matters; lead with the most important ref.
- Fallbacks: WaveSpeed hosts Seedance too; Kie AI has Seedance variants.
