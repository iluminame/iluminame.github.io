#!/usr/bin/env python3
"""Generate images via Kie.ai, fal.ai, or WaveSpeed (stdlib only).

Submits the job, polls until done, downloads results into the gallery folder,
and appends one JSON line per run to <out>/log.jsonl.

Examples:
  python3 generate_image.py --check-keys
  python3 generate_image.py --provider kie --model google/nano-banana-pro \
      --prompt "..." --aspect 4:5 --count 2 --cost 0.05 --out generations
  python3 generate_image.py --provider fal --model fal-ai/flux/dev \
      --prompt "..." --aspect 16:9 --count 4 --cost 0.03 --out generations --dry-run
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

KEYS = {
    "kie": "KIE_API_KEY",
    "fal": "FAL_KEY",
    "wavespeed": "WAVESPEED_API_KEY",
}

# fal uses named size presets; map common aspect ratios to them.
FAL_SIZES = {
    "1:1": "square_hd",
    "4:3": "landscape_4_3",
    "3:4": "portrait_4_3",
    "16:9": "landscape_16_9",
    "9:16": "portrait_16_9",
    "4:5": "portrait_4_3",
    "21:9": "landscape_16_9",
}


def http_json(url, payload=None, headers=None, timeout=120):
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


def auth_headers(provider, key):
    if provider == "fal":
        return {"Authorization": f"Key {key}"}
    return {"Authorization": f"Bearer {key}"}


def to_data_uri(path):
    mime = mimetypes.guess_type(path)[0] or "image/png"
    with open(path, "rb") as f:
        return f"data:{mime};base64," + base64.b64encode(f.read()).decode()


def build_request(args, image_refs):
    """Return (url, payload) for the submit call of each provider."""
    if args.provider == "kie":
        inp = {"prompt": args.prompt}
        if args.aspect:
            inp["aspect_ratio"] = args.aspect
        if args.resolution:
            inp["resolution"] = args.resolution
        if image_refs:
            inp["image_urls"] = image_refs
        if args.input_json:
            inp.update(json.loads(args.input_json))
        return "https://api.kie.ai/api/v1/jobs/createTask", {"model": args.model, "input": inp}

    if args.provider == "fal":
        inp = {"prompt": args.prompt, "num_images": args.count}
        if args.aspect:
            inp["image_size"] = FAL_SIZES.get(args.aspect, args.aspect)
        if image_refs:
            inp["image_url" if len(image_refs) == 1 else "image_urls"] = (
                image_refs[0] if len(image_refs) == 1 else image_refs)
        if args.input_json:
            inp.update(json.loads(args.input_json))
        return f"https://queue.fal.run/{args.model}", inp

    # wavespeed
    inp = {"prompt": args.prompt}
    if args.input_json:
        inp.update(json.loads(args.input_json))
    if image_refs:
        inp["images"] = image_refs
    return f"https://api.wavespeed.ai/api/v3/{args.model}", inp


def poll_kie(task_id, headers):
    url = f"https://api.kie.ai/api/v1/jobs/recordInfo?taskId={urllib.parse.quote(task_id)}"
    while True:
        d = http_json(url, headers=headers).get("data") or {}
        state = d.get("state")
        if state == "success":
            result = json.loads(d.get("resultJson") or "{}")
            return result.get("resultUrls") or result.get("result_urls") or []
        if state == "fail":
            sys.exit(f"Kie.ai job failed: {d.get('failMsg')}")
        print(f"  … {state}", flush=True)
        time.sleep(5)


def poll_fal(submit_resp, headers):
    status_url = submit_resp["status_url"]
    while True:
        s = http_json(status_url, headers=headers)
        if s.get("status") == "COMPLETED":
            r = http_json(submit_resp["response_url"], headers=headers)
            imgs = r.get("images") or ([r["image"]] if r.get("image") else [])
            return [i["url"] if isinstance(i, dict) else i for i in imgs]
        print(f"  … {s.get('status')}", flush=True)
        time.sleep(4)


def poll_wavespeed(pred_id, headers):
    url = f"https://api.wavespeed.ai/api/v3/predictions/{pred_id}/result"
    while True:
        d = http_json(url, headers=headers).get("data") or {}
        status = d.get("status")
        if status == "completed":
            return d.get("outputs") or []
        if status == "failed":
            sys.exit(f"WaveSpeed job failed: {d.get('error')}")
        print(f"  … {status}", flush=True)
        time.sleep(4)


def slugify(text, maxlen=40):
    s = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return s[:maxlen].rstrip("-") or "gen"


def download(urls, out_dir, slug):
    os.makedirs(out_dir, exist_ok=True)
    paths = []
    for i, u in enumerate(urls, 1):
        ext = os.path.splitext(urllib.parse.urlparse(u).path)[1] or ".png"
        path = os.path.join(out_dir, f"{slug}-{int(time.time())}-{i}{ext}")
        with urllib.request.urlopen(u, timeout=300) as r, open(path, "wb") as f:
            f.write(r.read())
        paths.append(path)
        print(f"saved: {path}")
    return paths


def log_run(out_root, entry):
    os.makedirs(out_root, exist_ok=True)
    with open(os.path.join(out_root, "log.jsonl"), "a") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--provider", choices=list(KEYS), help="kie | fal | wavespeed")
    p.add_argument("--model", help="provider model ID (see references/providers.md)")
    p.add_argument("--prompt", help="full production prompt")
    p.add_argument("--aspect", default="", help="aspect ratio, e.g. 1:1, 4:5, 16:9")
    p.add_argument("--resolution", default="", help="kie only, e.g. 1K, 2K, 4K")
    p.add_argument("--count", type=int, default=1, help="number of images (fal batches; kie/wavespeed loop)")
    p.add_argument("--image-url", action="append", default=[], help="source image (URL or local path) for edit models; repeatable")
    p.add_argument("--input-json", help="extra provider-specific input fields as JSON")
    p.add_argument("--cost", type=float, default=0.0, help="estimated USD cost PER IMAGE, for the log")
    p.add_argument("--out", default="generations", help="gallery root folder")
    p.add_argument("--style", default="", help="style preset name, for the log")
    p.add_argument("--dry-run", action="store_true", help="print the request and exit without spending")
    p.add_argument("--check-keys", action="store_true", help="report which provider keys are set")
    args = p.parse_args()

    if args.check_keys:
        for prov, var in KEYS.items():
            print(f"{prov:10s} {var:20s} {'SET' if os.environ.get(var) else 'missing'}")
        return
    for req in ("provider", "model", "prompt"):
        if not getattr(args, req):
            p.error(f"--{req} is required (or use --check-keys)")

    key = os.environ.get(KEYS[args.provider])
    if not key and not args.dry_run:
        sys.exit(f"Missing {KEYS[args.provider]} env var for provider '{args.provider}'.")

    image_refs = [to_data_uri(u) if os.path.exists(u) else u for u in args.image_url]
    url, payload = build_request(args, image_refs)
    runs = 1 if args.provider == "fal" else args.count  # fal batches natively

    if args.dry_run:
        print(f"POST {url}  x{runs}")
        print(json.dumps(payload, indent=2)[:3000])
        print(f"estimated cost: ~${args.cost * args.count:.2f} total")
        return

    headers = auth_headers(args.provider, key)
    date_dir = os.path.join(args.out, dt.date.today().isoformat())
    slug = slugify(args.prompt)
    all_paths = []
    for n in range(runs):
        print(f"submitting to {args.provider} ({n + 1}/{runs}) …", flush=True)
        resp = http_json(url, payload, headers)
        if args.provider == "kie":
            if resp.get("code") != 200:
                sys.exit(f"Kie.ai error: {resp.get('msg') or resp}")
            urls = poll_kie(resp["data"]["taskId"], headers)
        elif args.provider == "fal":
            urls = poll_fal(resp, headers)
        else:
            if resp.get("code") not in (200, None):
                sys.exit(f"WaveSpeed error: {resp.get('message') or resp}")
            urls = poll_wavespeed(resp["data"]["id"], headers)
        all_paths += download(urls, date_dir, slug)

    total = args.cost * max(len(all_paths), args.count)
    log_run(args.out, {
        "ts": dt.datetime.now().isoformat(timespec="seconds"),
        "type": "image", "provider": args.provider, "model": args.model,
        "prompt": args.prompt, "style": args.style, "aspect": args.aspect,
        "files": all_paths, "est_cost_usd": round(total, 4),
    })
    print(f"\ndone: {len(all_paths)} file(s), estimated ~${total:.2f}")


if __name__ == "__main__":
    main()
