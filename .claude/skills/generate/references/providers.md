# Providers: keys, auth shapes, and maintenance

You don't need accounts with every AI lab. Aggregators host many models
behind one key and one bill. Model-specific details (endpoint, request shape,
response handling) live in `models/*.md` — this file covers what's shared:
auth, uploads, fallback order, troubleshooting, and how to add a new model.

## The keys

| Provider | Sign up at | Key name in `.env` | Why it's here |
|---|---|---|---|
| Kie AI | kie.ai | `KIE_API_KEY` | Often the cheapest route for popular models. Handy file upload for turning local images into public URLs. |
| fal.ai | fal.ai | `FAL_KEY` | Fast, huge model catalog, the best docs. **First fallback.** |
| WaveSpeed AI | wavespeed.ai | `WAVESPEED_API_KEY` | Broad catalog, useful when the other two lack a model or reject a job. **Second fallback.** |
| Google AI Studio | aistudio.google.com | `GEMINI_API_KEY` | Direct source for Nano Banana 2 (images) and Veo 3.1 (video). |

Store them in a `.env` file, keep it out of git (`.gitignore` covers it),
and read keys from the environment — never paste them into code or chat.

## Each provider authenticates differently

The single thing that trips people up. Same idea, three shapes — get it
right once per provider and every model on that provider works:

```
GOOGLE AI STUDIO — key goes in the URL
POST …/models/{model-id}:generateContent?key={GEMINI_API_KEY}

FAL.AI — header, the word Key
POST https://fal.run/{model-id}        (or queue.fal.run for async)
Authorization: Key {FAL_KEY}

KIE AI — header, the word Bearer
POST https://api.kie.ai/api/v1/jobs/createTask
Authorization: Bearer {KIE_API_KEY}

WAVESPEED — header, the word Bearer
POST https://api.wavespeed.ai/api/v3/{model-path}
Authorization: Bearer {WAVESPEED_API_KEY}
```

## Sync or async, per model

Sync models (GPT Image 2, Nano Banana 2, Seedance via queue) reply with the
finished result in one call. Async models (Kling, Veo) hand you a job id;
poll a status endpoint every 5–15 seconds until it says done, then download
**immediately** — result URLs often expire in hours. Each recipe file states
which pattern its model uses, because getting this backwards is the most
common reason a first attempt appears to hang.

Generic async pattern:
1. POST the job → reply contains a task/operation id
2. Poll the status URL every 5–15 seconds, patiently
3. Status says complete → reply now contains a file URL
4. Download immediately
5. Save into the generations folder, then write the sidecar log

## Kie file upload (local image → public URL)

Kie's Kling endpoint needs public `image_urls`. For a local ref, upload it to
Kie first (docs: docs.kie.ai, "File Upload" — endpoint of the form
`POST https://kieai.redpandaai.co/api/file-stream-upload` with
`Authorization: Bearer $KIE_API_KEY`, multipart `file` field; the reply
contains the hosted URL). If the upload API gives trouble, the pragmatic
fallback is routing that job through fal.ai instead, which accepts base64
`data:` URIs directly.

## What generations roughly cost

| Job | Ballpark | Note |
|---|---|---|
| Draft image, cheap model | $0.01–0.03 | The default. Iterate freely here. |
| Quality image, top model | $0.05–0.15 | For finals only, after a draft is picked. |
| Video, per second | $0.20–0.35 | A 10-second clip is $2–3.50. This is why cost gates exist. |

Prices move fast — treat these as ballparks and check the provider's pricing
page before relying on them. Anchor for "is this cheaper than a
subscription?": Higgsfield-style plans run ~$49/month ≈ $0.31–0.34 per image.

## Adding a new model (recipe template)

Models change monthly. When a better one ships, add one markdown file to
`models/` and the skill learns it — nothing else changes. Ten minutes, once:

```markdown
# Model Name
One line on what this model is best at and when to pick it.

| Field | Value |
|---|---|
| Model ID | the-exact-model-id |
| Provider | Kie AI / fal.ai / WaveSpeed AI / Google AI Studio |
| Method | Sync (instant reply) or Async (submit, then poll) |
| Type | Image or Video |
| API key | .env -> KEY_NAME |
| Docs | link to the provider's page for this model |
| Cost | rough price per image / per second |

## Endpoint
POST https://...

## Request format
(the exact JSON body from the docs: prompt, aspect ratio, resolution,
reference image fields)

## Response handling
(where the image/video lives in the reply: base64 field or URL to download.
For async: the status endpoint and the field that says "done".)

## Notes
(gotchas: rate limits, max sizes, content rules, upload quirks)
```

## Manual curl fallback (chat sandbox without network)

Build the exact commands from the recipe file for the user to run locally:

```bash
# 1) Submit (Kie example — async)
curl -s -X POST https://api.kie.ai/api/v1/jobs/createTask \
  -H "Authorization: Bearer $KIE_API_KEY" -H "Content-Type: application/json" \
  -d '{"model":"kling-3.0/video","input":{"prompt":"<PROMPT>","duration":5,"aspect_ratio":"16:9"}}'
# 2) Poll until state=success
curl -s "https://api.kie.ai/api/v1/jobs/recordInfo?taskId=<TASKID>" \
  -H "Authorization: Bearer $KIE_API_KEY"
# 3) Download from resultJson.resultUrls, save as {project}_{desc}_{timestamp}.mp4
curl -o acme_orbit_1774912000.mp4 "<RESULT_URL>"
```

Then have the user report the file names back, and write the sidecar `.json`
entries yourself so the library and cost stats stay accurate.

## Troubleshooting

| Symptom | Likely cause → fix |
|---|---|
| 401 / Unauthorized | Wrong or missing env var → `generate_image.py --check-keys`; regenerate key |
| "model not found" / 404 | ID changed → open the provider's model page, copy the id fresh, update the recipe file |
| 402 / insufficient credits | Top up that provider; report spend from `gallery.py --stats` |
| Kie `code != 200` schema msg | Input field names differ per model → the model page's API tab has the exact schema |
| Job seems to hang | Sync/async mixed up → check the recipe's Method row; async needs polling |
| Stuck in queue >10 min | Peak load → keep polling or fall back to the next provider (say so) |
| Content policy rejection | Rephrase (no celebrity/brand/NSFW terms); tell the user why |
| Result URL 404s later | Expected — that's why files are downloaded immediately |
