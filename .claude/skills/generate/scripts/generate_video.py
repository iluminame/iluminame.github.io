#!/usr/bin/env python3
"""Generate video via fal.ai, Kie.ai, or WaveSpeed (stdlib only).

Same submit → poll → download → log loop as generate_image.py, tuned for video
jobs (longer polling, single output, image→video support).

Examples:
  python3 generate_video.py --provider fal \
      --model fal-ai/bytedance/seedance/v1/lite/text-to-video \
      --prompt "..." --duration 5 --aspect 16:9 --cost 0.15 --out generations
  python3 generate_video.py --provider fal \
      --model fal-ai/kling-video/v2.5-turbo/pro/image-to-video \
      --prompt "slow orbit around the product" \
      --image-url generations/2026-07-31/ad-1.png --cost 0.35 --out generations
"""
import argparse
import base64
import datetime as dt
import json
import mimetypes
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

KEYS = {"kie": "KIE_API_KEY", "fal": "FAL_KEY", "wavespeed": "WAVESPEED_API_KEY"}


def http_json(url, payload=None, headers=None, timeout=180):
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(url, data=data, headers=headers or {})
    if data is not None:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")[:2000]
        sys.exit(f"HTTP {e.code} from {url}\n{body}")


def to_data_uri(path):
    mime = mimetypes.guess_type(path)[0] or "image/png"
    with open(path, "rb") as f:
        return f"data:{mime};base64," + base64.b64encode(f.read()).decode()


def slugify(text, maxlen=40):
    s = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return s[:maxlen].rstrip("-") or "gen"


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--provider", choices=list(KEYS), required=True)
    p.add_argument("--model", required=True, help="provider model ID (see references/providers.md)")
    p.add_argument("--prompt", required=True)
    p.add_argument("--duration", type=int, default=5, help="seconds, model permitting")
    p.add_argument("--aspect", default="16:9")
    p.add_argument("--resolution", default="", help="e.g. 720p, 1080p (model permitting)")
    p.add_argument("--image-url", default="", help="source frame for image-to-video (URL or local path)")
    p.add_argument("--input-json", help="extra provider-specific input fields as JSON")
    p.add_argument("--cost", type=float, default=0.0, help="estimated USD cost for this clip, for the log")
    p.add_argument("--out", default="generations")
    p.add_argument("--style", default="", help="style preset name, for the log")
    p.add_argument("--timeout-min", type=int, default=15, help="max minutes to wait")
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()

    key = os.environ.get(KEYS[args.provider])
    if not key and not args.dry_run:
        sys.exit(f"Missing {KEYS[args.provider]} env var for provider '{args.provider}'.")

    image_ref = args.image_url
    if image_ref and os.path.exists(image_ref):
        image_ref = to_data_uri(image_ref)

    if args.provider == "kie":
        inp = {"prompt": args.prompt, "aspect_ratio": args.aspect}
        if args.duration:
            inp["duration"] = args.duration
        if args.resolution:
            inp["resolution"] = args.resolution
        if image_ref:
            inp["image_urls"] = [image_ref]
        if args.input_json:
            inp.update(json.loads(args.input_json))
        url, payload = "https://api.kie.ai/api/v1/jobs/createTask", {"model": args.model, "input": inp}
        headers = {"Authorization": f"Bearer {key}"}
    elif args.provider == "fal":
        inp = {"prompt": args.prompt, "aspect_ratio": args.aspect}
        if args.duration:
            inp["duration"] = str(args.duration)
        if args.resolution:
            inp["resolution"] = args.resolution
        if image_ref:
            inp["image_url"] = image_ref
        if args.input_json:
            inp.update(json.loads(args.input_json))
        url, payload = f"https://queue.fal.run/{args.model}", inp
        headers = {"Authorization": f"Key {key}"}
    else:
        inp = {"prompt": args.prompt, "duration": args.duration}
        if image_ref:
            inp["image"] = image_ref
        if args.input_json:
            inp.update(json.loads(args.input_json))
        url, payload = f"https://api.wavespeed.ai/api/v3/{args.model}", inp
        headers = {"Authorization": f"Bearer {key}"}

    if args.dry_run:
        print(f"POST {url}")
        print(json.dumps(payload, indent=2)[:3000])
        print(f"estimated cost: ~${args.cost:.2f}")
        return

    print(f"submitting video job to {args.provider} … (typical wait: 1–6 min)", flush=True)
    resp = http_json(url, payload, headers)
    deadline = time.time() + args.timeout_min * 60

    video_urls = []
    if args.provider == "kie":
        if resp.get("code") != 200:
            sys.exit(f"Kie.ai error: {resp.get('msg') or resp}")
        poll = f"https://api.kie.ai/api/v1/jobs/recordInfo?taskId={urllib.parse.quote(resp['data']['taskId'])}"
        while time.time() < deadline:
            d = http_json(poll, headers=headers).get("data") or {}
            if d.get("state") == "success":
                result = json.loads(d.get("resultJson") or "{}")
                video_urls = result.get("resultUrls") or []
                break
            if d.get("state") == "fail":
                sys.exit(f"Kie.ai job failed: {d.get('failMsg')}")
            print(f"  … {d.get('state')}", flush=True)
            time.sleep(10)
    elif args.provider == "fal":
        while time.time() < deadline:
            s = http_json(resp["status_url"], headers=headers)
            if s.get("status") == "COMPLETED":
                r = http_json(resp["response_url"], headers=headers)
                v = r.get("video") or {}
                video_urls = [v["url"]] if v.get("url") else [u["url"] for u in r.get("videos", [])]
                break
            print(f"  … {s.get('status')}", flush=True)
            time.sleep(10)
    else:
        if resp.get("code") not in (200, None):
            sys.exit(f"WaveSpeed error: {resp.get('message') or resp}")
        poll = f"https://api.wavespeed.ai/api/v3/predictions/{resp['data']['id']}/result"
        while time.time() < deadline:
            d = http_json(poll, headers=headers).get("data") or {}
            if d.get("status") == "completed":
                video_urls = d.get("outputs") or []
                break
            if d.get("status") == "failed":
                sys.exit(f"WaveSpeed job failed: {d.get('error')}")
            print(f"  … {d.get('status')}", flush=True)
            time.sleep(10)

    if not video_urls:
        sys.exit(f"Timed out after {args.timeout_min} min — the job may still finish; re-poll or check the provider dashboard.")

    date_dir = os.path.join(args.out, dt.date.today().isoformat())
    os.makedirs(date_dir, exist_ok=True)
    slug = slugify(args.prompt)
    paths = []
    for i, u in enumerate(video_urls, 1):
        ext = os.path.splitext(urllib.parse.urlparse(u).path)[1] or ".mp4"
        path = os.path.join(date_dir, f"{slug}-{int(time.time())}-{i}{ext}")
        with urllib.request.urlopen(u, timeout=600) as r, open(path, "wb") as f:
            f.write(r.read())
        paths.append(path)
        print(f"saved: {path}")

    os.makedirs(args.out, exist_ok=True)
    with open(os.path.join(args.out, "log.jsonl"), "a") as f:
        f.write(json.dumps({
            "ts": dt.datetime.now().isoformat(timespec="seconds"),
            "type": "video", "provider": args.provider, "model": args.model,
            "prompt": args.prompt, "style": args.style, "aspect": args.aspect,
            "duration_s": args.duration, "files": paths,
            "est_cost_usd": round(args.cost, 4),
        }, ensure_ascii=False) + "\n")
    print(f"\ndone: {len(paths)} clip(s), estimated ~${args.cost:.2f}")


if __name__ == "__main__":
    main()
