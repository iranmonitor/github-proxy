#!/usr/bin/env python3
import os
import re
from urllib.parse import urlparse, urljoin
import requests
from flask import Flask, Response, abort, send_from_directory, request, redirect

app = Flask(__name__)

# Proxy domain
PROXY_DOMAIN = "github.iranmonitor.net"

# Allowed upstream GitHub hosts (suffixes / exact)
ALLOWED_HOST_SUFFIXES = (
    ".github.com",
    ".githubusercontent.com",
    "api.github.com",
    "release-assets.githubusercontent.com",
)

# Folder containing index.html
APP_DIR = os.path.dirname(os.path.abspath(__file__))

# Regex for rewriting URLs in text:
#  - full scheme: https?://<host>/
#  - protocol-relative: //host/
#  - bare host/path (avoid rewriting already proxied urls)
_scheme_pattern = re.compile(
    r"(https?://)([A-Za-z0-9\-.]+(?:(?:\.github\.com)|(?:\.githubusercontent\.com)|(?:api\.github\.com)|(?:release-assets\.githubusercontent\.com)|(?:release-assets\.githubusercontent\.com)|(?:release-assets\.githubusercontent\.com)|(?:release-assets\.githubusercontent\.com)|(?:release-assets.githubusercontent\.com)))(/)",
    flags=re.IGNORECASE,
)
# (the above includes release-assets.githubusercontent.com)
_protocol_rel_pattern = re.compile(
    r"(?<![:/])//([A-Za-z0-9\-.]+(?:(?:\.github\.com)|(?:\.githubusercontent\.com)|api\.github\.com|release-assets\.githubusercontent\.com|release-assets.githubusercontent\.com))(/)",
    flags=re.IGNORECASE,
)
_prefix_escaped = re.escape(f"https://{PROXY_DOMAIN}/")
_bare_pattern = re.compile(
    rf"(?<!{_prefix_escaped})\b([A-Za-z0-9\-.]+(?:(?:\.github\.com)|(?:\.githubusercontent\.com)|api\.github\.com|release-assets\.githubusercontent\.com|release-assets.githubusercontent\.com))(/)",
    flags=re.IGNORECASE,
)


def host_allowed(host: str) -> bool:
    """Allow upstream GitHub hosts or the proxy itself."""
    if not host:
        return False
    host = host.lower()
    if host == PROXY_DOMAIN:
        return True
    return any(host == suf.lstrip(".") or host.endswith(suf) for suf in ALLOWED_HOST_SUFFIXES)


def map_proxy_to_upstream(host: str, path: str) -> str:
    """
    Map proxy request path -> upstream URL.

    Rules:
      - If the request was made to the proxy host:
        * If first path segment contains a dot, treat it as an explicit upstream host:
            github.iranmonitor.net/raw.githubusercontent.com/owner/... -> https://raw.githubusercontent.com/owner/...
        * If path looks like owner/repo/releases/... -> github.com/... (so GitHub can redirect to release-assets)
        * If path looks like owner/repo/blob/<branch>/... or owner/repo/raw/<branch>/... -> raw.githubusercontent.com/owner/repo/<branch>/...
        * If path looks like owner/repo/<branch>/... -> raw.githubusercontent.com/owner/repo/<branch>/...
        * owner/repo -> github.com/owner/repo
      - If host != PROXY_DOMAIN: forward to that host.
    """
    host = host.lower()
    if host == PROXY_DOMAIN:
        parts = path.split("/", 1)
        first = parts[0].lower() if parts else ""
        rest = parts[1] if len(parts) > 1 else ""

        # explicit upstream host in first segment
        if "." in first:
            upstream_host = first
            upstream_path = rest
            return f"https://{upstream_host}/{upstream_path}" if upstream_path else f"https://{upstream_host}/"

        segs = path.split("/")
        if len(segs) >= 3:
            owner, repo, third = segs[0], segs[1], segs[2]

            # keep releases on github.com (so GitHub returns signed release-assets redirect)
            if third == "releases":
                return f"https://github.com/{path}"

            # blob/raw -> map to raw.githubusercontent.com
            if third in ("blob", "raw"):
                rest_after = "/".join(segs[3:]) if len(segs) > 3 else ""
                return f"https://raw.githubusercontent.com/{owner}/{repo}/{rest_after}"

            # otherwise treat as branch/path -> raw.githubusercontent.com/owner/repo/<branch>/<...>
            rest_after_branch = "/".join(segs[2:])
            return f"https://raw.githubusercontent.com/{owner}/{repo}/{rest_after_branch}"

        if len(segs) == 2:
            # owner/repo -> github HTML project page
            return f"https://github.com/{path}"

        # fallback -> github.com root or whatever was requested
        return f"https://github.com/{path}"

    else:
        # client requested a different host directly; forward to it
        return f"https://{host}/{path}"


def rewrite_upstream_hosts_to_proxy(text: str) -> str:
    """Rewrite upstream URLs in text content to use the proxy."""

    def _scheme_repl(m):
        host = m.group(2)
        return f"https://{PROXY_DOMAIN}/{host}/"

    # rewrite full https://host/...
    text = _scheme_pattern.sub(_scheme_repl, text)
    # rewrite protocol-relative //host/...
    text = _protocol_rel_pattern.sub(rf"https://{PROXY_DOMAIN}/\1/", text)
    # rewrite bare host/... occurrences (avoid already-proxied)
    text = _bare_pattern.sub(rf"https://{PROXY_DOMAIN}/\1/", text)
    return text


@app.before_request
def enforce_https():
    proto = request.headers.get("X-Forwarded-Proto", "")
    is_secure = (proto == "https") or request.is_secure
    if not is_secure:
        url = request.url.replace("http://", "https://", 1)
        return redirect(url, code=301)


@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def proxy(path):
    # Serve index.html at root
    if path == "":
        return send_from_directory(APP_DIR, "index.html")

    # Build upstream URL
    host_header = request.host.split(":")[0]
    target_url = map_proxy_to_upstream(host_header, path)
    if request.query_string:
        qs = request.query_string.decode("utf-8", errors="ignore")
        target_url = f"{target_url}?{qs}"

    try:
        upstream_host = urlparse(target_url).hostname
    except Exception:
        return abort(400, "Bad URL")

    if not host_allowed(upstream_host):
        return abort(403, f"Upstream host not allowed: {upstream_host}")

    # Forward selected headers but force identity encoding so we can rewrite safely
    upstream_headers = {}
    for h in ("User-Agent", "Accept", "Authorization", "Cookie"):
        if h in request.headers:
            upstream_headers[h] = request.headers[h]
    # Force identity encoding: avoid compressed payloads (so rewriting works reliably)
    upstream_headers["Accept-Encoding"] = "identity"

    try:
        upstream = requests.get(
            target_url,
            stream=True,
            timeout=30,
            allow_redirects=False,  # handle redirects manually
            headers=upstream_headers,
        )
    except requests.RequestException as e:
        return abort(502, f"Error contacting upstream: {e}")

    # Handle redirects by parsing Location and rewriting to proxy if upstream host allowed
    if 300 <= upstream.status_code < 400 and "Location" in upstream.headers:
        loc = upstream.headers["Location"]
        abs_loc = urljoin(target_url, loc)
        parsed = urlparse(abs_loc)
        if parsed.hostname and host_allowed(parsed.hostname):
            # convert to proxied location: https://PROXY_DOMAIN/<upstream-host><path>?<query>
            proxied = f"https://{PROXY_DOMAIN}/{parsed.hostname}{parsed.path or '/'}"
            if parsed.query:
                proxied += f"?{parsed.query}"
            return redirect(proxied, code=upstream.status_code)
        # fallback: let client follow absolute upstream redirect
        return redirect(abs_loc, code=upstream.status_code)

    # preserve headers for response
    content_type = upstream.headers.get("Content-Type", "application/octet-stream")
    headers = {"Content-Type": content_type}
    cd = upstream.headers.get("Content-Disposition")
    if cd:
        headers["Content-Disposition"] = cd

    # decide if this is text-like and should be rewritten
    ct_lower = content_type.lower() if content_type else ""
    text_like = any(x in ct_lower for x in ("text", "json", "xml", "javascript", "script", "plain", "sh"))

    if text_like:
        try:
            # upstream.content will be decoded because we asked identity (no gzip), but keep fallback decoding
            raw = upstream.content
            try:
                text = raw.decode("utf-8")
            except UnicodeDecodeError:
                text = raw.decode("latin1", errors="ignore")
            text = rewrite_upstream_hosts_to_proxy(text)
            return Response(text.encode("utf-8"), status=upstream.status_code, headers=headers)
        finally:
            upstream.close()
    else:
        # binary stream (do not buffer entire body)
        def generate():
            try:
                for chunk in upstream.iter_content(chunk_size=8192):
                    if chunk:
                        yield chunk
            finally:
                upstream.close()
        return Response(generate(), status=upstream.status_code, headers=headers)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    host = os.environ.get("HOST", "0.0.0.0")
    app.run(host=host, port=port)
