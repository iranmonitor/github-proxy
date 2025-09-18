# GitHub Raw Proxy for cPanel

> Persian/فارسی: [Description/توضیحات](https://github.com/iranmonitor/github-proxy/blob/main/README_FA.md)

A lightweight **Flask proxy** for `raw.githubusercontent.com`, designed for cPanel shared hosting.
✅ Automatically rewrites `raw.githubusercontent.com` links to your proxy domain so scripts work in blocked regions.

> Demo/test: [https://github.iranmonitor.net](https://github.iranmonitor.net)

### Features
- Flask + requests, deployable on cPanel
- Rewrites raw.githubusercontent.com → github.iranmonitor.net
- Supports scripts, JSON, configs; binary files pass through unchanged
- Works for developers in blocked regions

### Installation
1. Upload `proxy.py` and `requirements.txt` to **Application root** (e.g., `github-prox/`)
2. In cPanel → Setup Python App:
   - Python version: 3.9+
   - Startup file: `proxy.py`
   - Entry point: `app`
   - Run Pip Install from `requirements.txt`
3. Restart the app and assign a subdomain (e.g., `github.iranmonitor.net`)
4. Enable SSL for HTTPS if possible

### Usage
Original GitHub raw link:
```
https://raw.githubusercontent.com/user/repo/branch/file.sh
```
Proxy link:
```
https://github.iranmonitor.net/user/repo/branch/file.sh
```
All `raw.githubusercontent.com` references inside text files are replaced automatically.

### Notes
- For high traffic, caching is recommended
- Not intended for hosting large files
