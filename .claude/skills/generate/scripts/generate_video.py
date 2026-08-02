#!/usr/bin/env python3
"""Generate video via Kie.ai, fal.ai, WaveSpeed, or Google AI Studio (stdlib only).

Async-aware: submits the job, polls patiently (video takes 1–6 min), downloads
immediately (result URLs expire), saves FLAT as
{project}_{description}_{timestamp}.{ext} and writes the sidecar .json log.

REMEMBER THE COST GATE: quote model + duration + resolution + dollars and get
the user's explicit go before running this script. One approval = one run.

Examples:
  python3 generate_video.py --provider kie --model kling-3.0/video \
      --prompt "..." --duration 5 --aspect 16:9 --mode std \
      --project acme --desc orbit --cost 1.50
  python3 generate_video.py --provider fal \
      --model bytedance/seedance-2.0/fast/reference-to-video \
      --prompt "..." --ref generations/refs/a.png --ref generations/refs/b.png \
      --duration 5 --cost 1.21
  python3 generate_video.py --provider google --model veo-3.1-generate-preview \
      --prompt "..." --ref generations/acme_hero_1774912000.png --cost 3.00
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
    "google": "GEMINI_API_KEY",
    "kie": "KIE_API_KEY",
    "fal": "FAL_KEY",
    "wavespeed": "WAVESPEED_API_KEY",
}

PLACEHOLDERS = ("pega_tu_clave", "tu_clave", "your_key", "your_api_key", "xxx")


def load_env(start=None):
    """Load KEY=VALUE lines from .env (or env.txt) in the cwd or a parent.

    Same loader as generate_image.py — real environment variables win over
    the file, and template placeholder values are ignored.
    """
    d = os.path.abspath(start or os.getcwd())
    for _ in range(4):
        for name in (".env", "env.txt"):
            path = os.path.join(d, name)
            if not os.path.isfile(path):
                continue
            with open(path, encoding="utf-8", errors="replace") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#") or "=" not in line:
                        continue
                    k, v = line.split("=", 1)
                    k, v = k.strip(), v.strip().strip('"').strip("'")
                    if (not k or not v or os.environ.get(k)
                            or any(ph in v.lower() for ph in PLACEHOLDERS)):
                        continue
                    os.environ[k] = v
            return path
        parent = os.path.dirname(d)
        if parent == d:
            break
        d = parent
    return None


def http_json(url, payload=None, headers=None, timeout=300):
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(url, data=data, headers=headers or {})
    if data is not None:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")[:2000]
        sys.exit(f"HTTP {e.code} from {url.split('?')[0]}\n{body}")


def b64_file(path):
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode()


def to_data_uri(path):
    mime = mimetypes.guess_type(path)[0] or "image/png"
    return f"data:{mime};base64," + b64_file(path)


def slugify(text, maxlen=40):
    s = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return s[:maxlen].rstrip("-") or "gen"


def download(url, out_dir, project, desc, index=0):
    os.makedirs(out_dir, exist_ok=True)
    ext = os.path.splitext(urllib.parse.urlparse(url).path)[1] or ".mp4"
    stem = f"{project}_{desc}_{int(time.time())}" + (f"-{index}" if index else "")
    path = os.path.join(out_dir, stem + ext)
    with urllib.request.urlopen(url, timeout=900) as r, open(path, "wb") as f:
        f.write(r.read())
    return path


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--provider", choices=list(KEYS), required=True)
    p.add_argument("--model", required=True, help="exact model ID from the recipe file in models/")
    p.add_argument("--prompt", required=True)
    p.add_argument("--duration", type=int, default=5, help="seconds, model permitting")
    p.add_argument("--aspect", default="16:9")
    p.add_argument("--resolution", default="", help="e.g. 720p, 1080p")
    p.add_argument("--mode", default="", help="kie kling: std | pro")
    p.add_argument("--ref", action="append", default=[],
                   help="start frame / reference image(s): local path or URL; repeatable")
    p.add_argument("--input-json", help="extra provider-specific input fields as JSON")
    p.add_argument("--cost", type=float, default=0.0, help="quoted USD for this clip (goes in the sidecar log)")
    p.add_argument("--project", default="gen")
    p.add_argument("--desc", default="", help="short description for the filename (defaults to prompt slug)")
    p.add_argument("--out", default="generations", help="flat output folder")
    p.add_argument("--timeout-min", type=int, default=20)
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()

    args.desc = slugify(args.desc or args.prompt)
    args.project = slugify(args.project)
    env_path = load_env()
    key = os.environ.get(KEYS[args.provider], "")
    if not key and not args.dry_run:
        where = f"in {env_path}" if env_path else "in a .env file next to your generations folder"
        sys.exit(f"Missing {KEYS[args.provider]} for provider '{args.provider}' — set it {where}. "
                 "Run generate_image.py --check-keys to see what was found.")

    ref_uris = [to_data_uri(r) if os.path.exists(r) else r for r in args.ref]
    extra = json.loads(args.input_json) if args.input_json else {}

    # Build the submit request per provider (shapes documented in models/*.md)
    if args.provider == "kie":
        inp = {"prompt": args.prompt, "duration": args.duration, "aspect_ratio": args.aspect}
        if args.mode:
            inp["mode"] = args.mode
        if args.resolution:
            inp["resolution"] = args.resolution
        if ref_uris:
            inp["image_urls"] = ref_uris  # Kie needs PUBLIC urls — upload local files first (providers.md)
        inp.update(extra)
        url, payload = "https://api.kie.ai/api/v1/jobs/createTask", {"model": args.model, "input": inp}
        headers = {"Authorization": f"Bearer {key}"}
    elif args.provider == "fal":
        inp = {"prompt": args.prompt, "aspect_ratio": args.aspect, "duration": args.duration}
        if args.resolution:
            inp["resolution"] = args.resolution
        if ref_uris:
            inp["image_url" if len(ref_uris) == 1 else "image_urls"] = (
                ref_uris[0] if len(ref_uris) == 1 else ref_uris)
        inp.update(extra)
        url, payload = f"https://queue.fal.run/{args.model}", inp
        headers = {"Authorization": f"Key {key}"}
    elif args.provider == "google":
        inst = {"prompt": args.prompt}
        if args.ref:
            local = args.ref[0]
            if os.path.exists(local):
                inst["image"] = {"bytesBase64Encoded": b64_file(local),
                                 "mimeType": mimetypes.guess_type(local)[0] or "image/png"}
            else:
                inst["image"] = {"gcsUri": local}
        payload = {"instances": [inst],
                   "parameters": {"aspectRatio": args.aspect, "sampleCount": 1, **extra}}
        url = (f"https://generativelanguage.googleapis.com/v1beta/models/"
               f"{args.model}:predictLongRunning?key={urllib.parse.quote(key)}")
        headers = {}
    else:  # wavespeed
        inp = {"prompt": args.prompt, "duration": args.duration}
        if ref_uris:
            inp["image"] = ref_uris[0]
        inp.update(extra)
        url, payload = f"https://api.wavespeed.ai/api/v3/{args.model}", inp
        headers = {"Authorization": f"Bearer {key}"}

    if args.dry_run:
        shown = url if args.provider != "google" else url.split("?")[0] + "?key=…"
        print(f"POST {shown}")
        body = dict(payload)
        if args.provider == "google" and body.get("instances", [{}])[0].get("image", {}).get("bytesBase64Encoded"):
            body = json.loads(json.dumps(body))
            body["instances"][0]["image"]["bytesBase64Encoded"] = "<base64…>"
        print(json.dumps(body, indent=2)[:3000])
        print(f"quoted cost: ~${args.cost:.2f}")
        return

    print(f"submitting video job to {args.provider} … (typical wait: 1–6 min)", flush=True)
    resp = http_json(url, payload, headers)
    deadline = time.time() + args.timeout_min * 60
    video_urls = []

    if args.provider == "kie":
        if resp.get("code") != 200:
            sys.exit(f"Kie.ai error: {resp.get('msg') or resp}")
        poll = ("https://api.kie.ai/api/v1/jobs/recordInfo?taskId="
                + urllib.parse.quote(resp["data"]["taskId"]))
        while time.time() < deadline:
            d = http_json(poll, headers=headers).get("data") or {}
            if d.get("state") == "success":
                video_urls = json.loads(d.get("resultJson") or "{}").get("resultUrls") or []
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
    elif args.provider == "google":
        op = resp.get("name")
        if not op:
            sys.exit(f"Unexpected Google reply: {json.dumps(resp)[:800]}")
        poll = f"https://generativelanguage.googleapis.com/v1beta/{op}?key={urllib.parse.quote(key)}"
        while time.time() < deadline:
            d = http_json(poll)
            if d.get("done"):
                if d.get("error"):
                    sys.exit(f"Veo job failed: {d['error']}")
                samples = (((d.get("response") or {}).get("generateVideoResponse") or {})
                           .get("generatedSamples") or [])
                video_urls = [s["video"]["uri"] for s in samples if (s.get("video") or {}).get("uri")]
                # Google file URIs need the key appended to download
                video_urls = [u + (("&" if "?" in u else "?") + "key=" + urllib.parse.quote(key))
                              for u in video_urls]
                break
            print("  … running", flush=True)
            time.sleep(15)
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
        sys.exit(f"Timed out after {args.timeout_min} min — the job may still finish; "
                 "re-poll or check the provider dashboard before resubmitting (don't pay twice).")

    paths = []
    for i, u in enumerate(video_urls, 1):
        path = download(u, args.out, args.project, args.desc, i if len(video_urls) > 1 else 0)
        sidecar = os.path.splitext(path)[0] + ".json"
        with open(sidecar, "w") as f:
            json.dump({
                "model": args.model, "provider": args.provider, "type": "video",
                "prompt": args.prompt, "refs": args.ref,
                "params": {"aspect": args.aspect, "duration_s": args.duration,
                           "resolution": args.resolution or None, "mode": args.mode or None},
                "est_cost_usd": round(args.cost, 4),
                "created": dt.datetime.now().astimezone().isoformat(timespec="seconds"),
            }, f, indent=2, ensure_ascii=False)
        paths.append(path)
        print(f"saved: {path}  (+ sidecar .json)")
    print(f"\ndone: {len(paths)} clip(s), quoted ~${args.cost:.2f}")


if __name__ == "__main__":
    main()
