import requests
from flask import Flask, Response, abort

app = Flask(__name__)

# your proxy domain
PROXY_DOMAIN = "github.iranmonitor.net"

@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def proxy(path):
    # Construct the original GitHub raw URL
    url = f"https://raw.githubusercontent.com/{path}"

    try:
        resp = requests.get(url, timeout=20)
    except requests.RequestException as e:
        return abort(502, f"Error contacting GitHub: {e}")

    if resp.status_code != 200:
        return abort(resp.status_code)

    # Get content type
    content_type = resp.headers.get("Content-Type", "text/plain; charset=utf-8")

    content = resp.content
    # Only do string replacement if it's text-based
    if "text" in content_type or "json" in content_type or "xml" in content_type or "script" in content_type:
        try:
            text = content.decode("utf-8")
        except UnicodeDecodeError:
            text = content.decode("latin1", errors="ignore")

        # Replace any raw.githubusercontent.com references for extra accessibility to blocked git contents
        text = text.replace("raw.githubusercontent.com", PROXY_DOMAIN)
        content = text.encode("utf-8")

    headers = {"Content-Type": content_type}
    return Response(content, status=resp.status_code, headers=headers)
