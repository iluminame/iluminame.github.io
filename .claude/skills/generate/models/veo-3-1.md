# Veo 3.1

Higher quality video from a start frame (or text). Slower and pricier than
Kling — reach for it when Kling's motion isn't good enough for a hero shot,
or when native audio matters.

| Field | Value |
|---|---|
| Model ID | `veo-3.1-generate-preview` |
| Provider | Google AI Studio (also hosted on fal.ai and Kie as fallback) |
| Method | **Async** (long-running operation, then poll) |
| Type | Video · 8-second clips · 720p · 1–4 samples per call |
| API key | `.env` → `GEMINI_API_KEY` |
| Docs | https://ai.google.dev/gemini-api/docs/video |
| Cost | premium — dollars per clip, not cents; verify at ai.google.dev/pricing |

## Endpoint

```
POST https://generativelanguage.googleapis.com/v1beta/models/veo-3.1-generate-preview:predictLongRunning?key={GEMINI_API_KEY}
```

Key goes **in the URL** (Google's auth shape).

## Request format

```json
{
  "instances": [{
    "prompt": "cinematic slow crane up over …, ambient city sound",
    "image": { "bytesBase64Encoded": "<base64 start frame>", "mimeType": "image/png" }
  }],
  "parameters": { "aspectRatio": "16:9", "sampleCount": 1 }
}
```

`image` (start frame) is optional but is where Veo shines — generate the
frame first with Nano Banana 2, get approval, then animate it.

## Response handling

Async, Google-style long-running operation:
1. Reply: `{"name": "models/veo-3.1…/operations/abc123"}`
2. Poll `GET https://generativelanguage.googleapis.com/v1beta/{name}?key={GEMINI_API_KEY}`
   every 10–15 seconds until `"done": true`.
3. Video URI at `response.generateVideoResponse.generatedSamples[0].video.uri`
   — download immediately (append `&key=` if the URI requires auth).

## Notes

- **Cost gate always applies** — this is the expensive lane. Quote first,
  one approval = one run, `sampleCount: 1` unless the user asks for options.
- Veo renders native audio: describe ambient sound or put dialogue in quotes.
- Getting sync/async backwards is the most common reason a first attempt
  "hangs" — Veo is async, always poll.
