# GPT Image 2

Text inside images. Signs, posters, menus, packaging, UI mockups — anything
where words must render exactly. Pick it the first time a request needs
readable text; otherwise Nano Banana 2 is cheaper.

| Field | Value |
|---|---|
| Model ID | `openai/gpt-image-2` (edit endpoint adds `/edit`) |
| Provider | fal.ai |
| Method | Sync (one call, result in reply) |
| Type | Image |
| API key | `.env` → `FAL_KEY` |
| Docs | https://fal.ai/models/openai/gpt-image-2 |
| Cost | ~$0.05 per image at medium quality — verify on the model page |

## Endpoint

```
POST https://fal.run/openai/gpt-image-2          (text → image)
POST https://fal.run/openai/gpt-image-2/edit     (image + prompt → edited image)
```

Auth header uses the word **Key**: `Authorization: Key {FAL_KEY}`.
(The queue endpoint `https://queue.fal.run/openai/gpt-image-2` also works and
is what the bundled script uses — submit, then poll `status_url`.)

## Request format

```json
{
  "prompt": "poster that says \"GRAND OPENING\" in bold serif …",
  "image_size": "1024x1536",
  "quality": "medium",
  "num_images": 1
}
```

For `/edit`, add `image_urls: ["…"]` — public URLs or `data:` base64 URIs
(the script converts local refs automatically).

## Response handling

`images[0].url` in the reply (queue flow: poll `status_url` until
`COMPLETED`, then GET `response_url`). Download immediately.

## Notes

- Quote text in the prompt exactly, and keep on-image text short (≤6 words
  renders most reliably).
- `quality`: low/medium/high — price scales with it; medium is the sweet spot.
- Requests with brand logos: pass the real logo via `/edit` + refs, don't ask
  the model to draw it.
