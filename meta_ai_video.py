#!/usr/bin/env python3
"""
meta_ai_video.py

Helpers to poll meta.ai GraphQL endpoints for generated videos and download them.

Usage (example):
    from meta_ai_video import poll_for_completion, download_url, extract_video_urls
    session = requests.Session()
    # copy headers/cookies from your existing repo/session
    session.headers.update({...})
    session.cookies.update({...})
    poll_payload = {
        "av":"813590375178585",
        "fb_dtsg":"<your_fb_dtsg>",
        "jazoest":"<your_jazoest>",
        "lsd":"<your_lsd>",
        "variables": '{"prompt_id":"d0568ba3-7505-422f-9b3a-3994314084a9", ...}',
        "doc_id":"33369109306021488",
    }
    urls, json_obj = poll_for_completion(session, poll_payload, "https://www.meta.ai/api/graphql/")
    for i,u in enumerate(urls):
        download_url(session, u, f"video_{i}.mp4")
"""

import json
import time
import requests
from typing import Any, Dict, List, Optional, Set, Tuple


def extract_video_urls(obj: Any) -> List[str]:
    """
    Recursively search a JSON-like object for candidate video URLs.
    Looks for keys like 'video_url', 'generated_video_uri', 'progressive_url', and any string containing '.mp4', 'video-ord', 'fbcdn', or 'cdn'.
    Returns a sorted list of unique URLs.
    """
    urls: Set[str] = set()

    def walk(x: Any) -> None:
        if isinstance(x, dict):
            for k, v in x.items():
                lk = k.lower()
                # Fields strongly indicative of media
                if isinstance(v, str):
                    if lk in ("video_url", "generated_video_uri", "uri", "progressive_url", "downloadurl", "signedurl"):
                        urls.add(v)
                    if ".mp4" in v or "video-ord" in v or "fbcdn" in v or "cdn" in v or "s3" in v:
                        urls.add(v)
                else:
                    walk(v)
        elif isinstance(x, list):
            for it in x:
                walk(it)
        elif isinstance(x, str):
            if ".mp4" in x or "video-ord" in x or "fbcdn" in x or "cdn" in x or "s3" in x:
                urls.add(x)

    walk(obj)
    return sorted(urls)


def try_parse_json(resp: requests.Response) -> Optional[Dict]:
    """
    Attempt to parse response as JSON, return dict on success or None on failure.
    """
    try:
        return resp.json()
    except ValueError:
        # Some responses may be HTML or partial text; try a safe json.loads as fallback
        try:
            return json.loads(resp.text)
        except Exception:
            return None


def poll_for_completion(
    session: requests.Session,
    poll_payload: Dict[str, Any],
    graphql_url: str = "https://www.meta.ai/api/graphql/",
    max_wait: int = 300,
    interval: float = 2.0,
    raise_on_error: bool = True,
) -> Tuple[List[str], Dict]:
    """
    Poll the GraphQL endpoint by POSTing poll_payload until we find video URLs or timeout.

    - session: requests.Session pre-configured with cookies/headers (including x-fb-lsd / cookies if required).
    - poll_payload: dict to send as form data (or JSON) for the GraphQL poll. In your code you used form-encoded 'data'; pass same shape.
    - graphql_url: endpoint to POST to.
    - max_wait: overall timeout in seconds.
    - interval: seconds between polls.
    - raise_on_error: whether to raise if we receive repeated non-200 responses.

    Returns: (list_of_urls, last_json_response)
    """
    start = time.time()
    consecutive_errors = 0
    while True:
        r = session.post(graphql_url, data=poll_payload, timeout=60)
        if r.status_code != 200:
            consecutive_errors += 1
            if raise_on_error and consecutive_errors >= 5:
                raise RuntimeError(f"Received {consecutive_errors} consecutive non-200 responses (last: {r.status_code})")
        else:
            consecutive_errors = 0

        j = try_parse_json(r)
        if j:
            urls = extract_video_urls(j)
            if urls:
                return urls, j
        # else ignore non-json replies (HTML error pages) and continue
        if time.time() - start > max_wait:
            raise TimeoutError("Timed out waiting for generation (no video URL found)")
        time.sleep(interval)


def download_url(session: requests.Session, url: str, out_path: str) -> None:
    """
    Download the given URL to out_path using the provided session (preserves cookies/headers).
    """
    with session.get(url, stream=True, allow_redirects=True, timeout=120) as r:
        r.raise_for_status()
        with open(out_path, "wb") as fd:
            for chunk in r.iter_content(chunk_size=8192):
                if chunk:
                    fd.write(chunk)


if __name__ == "__main__":
    import os
    import argparse

    parser = argparse.ArgumentParser(description="Poll meta.ai GraphQL for generated videos and download them.")
    parser.add_argument("--doc-id", help="doc_id used in the GraphQL poll (e.g. 33369109306021488)", required=False)
    parser.add_argument("--variables", help="variables JSON string to send in poll payload", required=False)
    parser.add_argument("--out-dir", help="directory to save videos", default=".")
    parser.add_argument("--max-wait", type=int, help="timeout seconds", default=300)
    parser.add_argument("--interval", type=float, help="poll interval seconds", default=2.0)
    args = parser.parse_args()

    s = requests.Session()
    # Load environment variables for session tokens (do NOT commit real secrets)
    s.cookies.update({
        "abra_sess": os.environ.get("ABRA_SESS", "")
    })
    s.headers.update({
        "x-fb-lsd": os.environ.get("X_FB_LSD", ""),
        "x-asbd-id": os.environ.get("X_ASBD_ID", "359341"),
        "User-Agent": os.environ.get("USER_AGENT", "meta-ai-client/1.0"),
    })

    if not args.doc_id or not args.variables:
        print("Example usage requires --doc-id and --variables. See module docstring for integration example.")
        raise SystemExit(1)

    poll_payload = {
        "av": os.environ.get("META_AV", "813590375178585"),
        "__user": "0",
        "__a": "1",
        "__req": "1",
        "__hs": "",
        "dpr": "1",
        "fb_dtsg": os.environ.get("FB_DTSG", ""),
        "jazoest": os.environ.get("JAZOEST", ""),
        "lsd": os.environ.get("X_FB_LSD", ""),
        "server_timestamps": "true",
        "variables": args.variables,
        "doc_id": args.doc_id,
    }

    print("Polling for video URLs...")
    urls, j = poll_for_completion(s, poll_payload, max_wait=args.max_wait, interval=args.interval)
    print("Found URLs:", urls)
    os.makedirs(args.out_dir, exist_ok=True)
    for i, u in enumerate(urls):
        out = os.path.join(args.out_dir, f"video_{i}.mp4")
        print("Downloading", u, "->", out)
        download_url(s, u, out)
    print("Done.")
