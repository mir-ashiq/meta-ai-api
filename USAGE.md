# meta_ai_video usage

## Overview

The `meta_ai_video.py` helper module provides utilities for polling meta.ai GraphQL endpoints to retrieve generated videos and download them. This module is designed to integrate with the existing `meta-ai-api` repository and uses `requests.Session` for authenticated HTTP requests.

## Installation

The module requires the `requests` library, which is already included in the repository's dependencies:

```bash
pip install requests
```

## Integration

### Setting up Environment Variables

Before using the helper module, you need to set up the following environment variables with your Meta AI session tokens. These can be extracted from your browser's network inspector when using https://www.meta.ai/:

```bash
export FB_DTSG="your_fb_dtsg_token"
export JAZOEST="your_jazoest_token"
export X_FB_LSD="your_lsd_token"
export ABRA_SESS="your_abra_sess_cookie"
export META_AV="your_meta_av_value"  # Optional, defaults to "813590375178585"
export X_ASBD_ID="359341"  # Optional
export USER_AGENT="meta-ai-client/1.0"  # Optional
```

**Important**: Never commit real secrets to version control. Always use environment variables or secure configuration management.

### Basic Usage

Import the helper functions into your code:

```python
from meta_ai_video import poll_for_completion, download_url, extract_video_urls
import requests
import os

# Create a session with authentication headers and cookies
session = requests.Session()

# Set cookies from environment
session.cookies.update({
    "abra_sess": os.environ.get("ABRA_SESS", "")
})

# Set headers from environment
session.headers.update({
    "x-fb-lsd": os.environ.get("X_FB_LSD", ""),
    "x-asbd-id": os.environ.get("X_ASBD_ID", "359341"),
    "User-Agent": os.environ.get("USER_AGENT", "meta-ai-client/1.0"),
})

# Build the poll payload
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
    "variables": '{"prompt_id":"d0568ba3-7505-422f-9b3a-3994314084a9"}',
    "doc_id": "33369109306021488",
}

# Poll for video completion
urls, json_response = poll_for_completion(
    session, 
    poll_payload,
    graphql_url="https://www.meta.ai/api/graphql/",
    max_wait=300,  # Wait up to 5 minutes
    interval=2.0   # Poll every 2 seconds
)

# Download all found videos
for i, url in enumerate(urls):
    output_path = f"video_{i}.mp4"
    download_url(session, url, output_path)
    print(f"Downloaded: {output_path}")
```

### Using with the Existing MetaAI Class

You can integrate this module with the existing `MetaAI` class from the repository:

```python
from meta_ai_api import MetaAI
from meta_ai_video import poll_for_completion, download_url
import os

# Initialize MetaAI with authentication (if needed for video generation)
ai = MetaAI(fb_email=os.environ.get("FB_EMAIL"), fb_password=os.environ.get("FB_PASSWORD"))

# Use the MetaAI session with video polling
# After requesting video generation through the MetaAI API, you can poll for completion
# Note: You'll need to extract the prompt_id and doc_id from the MetaAI response

poll_payload = {
    "av": os.environ.get("META_AV", "813590375178585"),
    "fb_dtsg": os.environ.get("FB_DTSG", ""),
    "jazoest": os.environ.get("JAZOEST", ""),
    "lsd": os.environ.get("X_FB_LSD", ""),
    "variables": '{"prompt_id":"your_prompt_id"}',
    "doc_id": "your_doc_id",
}

urls, json_obj = poll_for_completion(ai.session, poll_payload)
for i, url in enumerate(urls):
    download_url(ai.session, url, f"generated_video_{i}.mp4")
```

## Command Line Interface

The module can also be run directly from the command line:

```bash
# Set environment variables first
export FB_DTSG="your_token"
export JAZOEST="your_token"
export X_FB_LSD="your_token"
export ABRA_SESS="your_cookie"

# Run the CLI
python meta_ai_video.py \
    --doc-id "33369109306021488" \
    --variables '{"prompt_id":"d0568ba3-7505-422f-9b3a-3994314084a9"}' \
    --out-dir ./videos \
    --max-wait 300 \
    --interval 2.0
```

## API Reference

### `extract_video_urls(obj: Any) -> List[str]`

Recursively searches a JSON-like object for candidate video URLs. Returns a sorted list of unique URLs found.

**Patterns matched:**
- Keys: `video_url`, `generated_video_uri`, `uri`, `progressive_url`, `downloadurl`, `signedurl`
- String content: `.mp4`, `video-ord`, `fbcdn`, `cdn`, `s3`

### `try_parse_json(resp: requests.Response) -> Optional[Dict]`

Safely parses a `requests.Response` object as JSON. Returns a dictionary on success or `None` on failure.

### `poll_for_completion(session, poll_payload, graphql_url, max_wait, interval, raise_on_error) -> Tuple[List[str], Dict]`

Polls the GraphQL endpoint until video URLs are found or timeout occurs.

**Parameters:**
- `session`: Pre-configured `requests.Session` with cookies and headers
- `poll_payload`: Dictionary to send as form-encoded data
- `graphql_url`: GraphQL endpoint URL (default: `"https://www.meta.ai/api/graphql/"`)
- `max_wait`: Maximum wait time in seconds (default: 300)
- `interval`: Polling interval in seconds (default: 2.0)
- `raise_on_error`: Raise exception on repeated errors (default: True)

**Returns:** `(list_of_urls, last_json_response)`

### `download_url(session: requests.Session, url: str, out_path: str) -> None`

Downloads a URL to the specified output path using the provided session.

**Parameters:**
- `session`: `requests.Session` to use for the download
- `url`: URL to download
- `out_path`: Local file path to save the downloaded content

## Security Notes

- Never hardcode authentication tokens in your code
- Always use environment variables or secure configuration management
- Do not commit `.env` files or files containing secrets to version control
- Ensure your `.gitignore` includes sensitive files

## Educational Purpose

This module is provided for educational purposes only. Users should adhere to Meta's terms of service and use the library responsibly.
