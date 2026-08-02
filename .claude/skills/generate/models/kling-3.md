# Kling 3.0

General video. The sensible default: good motion, fair price. Text-to-video
and image-to-video (start frame). Use it unless the request needs Veo-level
quality or reference-driven animation.

| Field | Value |
|---|---|
| Model ID | `kling-3.0/video` (check the exact id on the Kie model page — ids shift) |
| Provider | Kie AI |
| Method | **Async** (submit, then poll) |
| Type | Video · 3–15 seconds · std = 720p, pro = 1080p |
| API key | `.env` → `KIE_API_KEY` |
| Docs | https://kie.ai (search Kling → API tab has the exact input schema) |
| Cost | roughly $0.20–0.35 per second depending on std/pro — verify on the model page |

## Endpoint

```
POST https://api.kie.ai/api/v1/jobs/createTask
```

Auth header uses the word **Bearer**: `Authorization: Bearer {KIE_API_KEY}`.

## Request format

```json
{
  "model": "kling-3.0/video",
  "input": {
    "prompt": "slow dolly-in toward the product, atmospheric haze …",
    "duration": 5,
    "aspect_ratio": "16:9",
    "mode": "std",
    "image_urls": ["https://…start-frame…"]
  }
}
```

`image_urls` (start frame) must be a **public URL** — for a local file, use
Kie's file upload first (see `references/providers.md` → "Kie file upload"),
or fall back to fal.ai's Kling endpoint which accepts base64 data URIs.

## Response handling

Async pattern:
1. Reply: `{"code": 200, "data": {"taskId": "…"}}` — any other `code` is an
   error, message in `msg`.
2. Poll `GET https://api.kie.ai/api/v1/jobs/recordInfo?taskId=…` every 10–15
   seconds, patiently (typical 1–6 min).
3. `data.state` → `success`: parse `data.resultJson` (a JSON **string**) →
   `resultUrls[0]` is the video URL. `fail`: read `data.failMsg`.
4. Download immediately — result URLs often expire in hours.

## Notes

- **Cost gate applies**: quote model + duration + resolution + dollars and
  wait for the user's explicit go before submitting.
- std/720p first; pro/1080p only for the approved final.
- Fallbacks: fal.ai (search "kling" at fal.ai/models), then WaveSpeed.
