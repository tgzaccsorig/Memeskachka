import io
import os
import re
import time
import zipfile
from pathlib import Path
from urllib.parse import quote

import requests
from flask import Flask, jsonify, render_template, send_file, request

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024
OUT_DIR = Path("generated")
OUT_DIR.mkdir(exist_ok=True)

COMMONS_API = "https://commons.wikimedia.org/w/api.php"
HEADERS = {"User-Agent": "MemeVault/1.0 (personal offline video collection; contact: admin@example.com)"}
SEARCH_TERMS = [
    "funny animal video", "cat funny video", "dog funny video",
    "comedy short video", "funny fail video", "slapstick video",
    "funny bird video", "cute animal video"
]

def commons_search(term, offset=0):
    params = {
        "action": "query", "format": "json", "generator": "search",
        "gsrsearch": f'filetype:video {term}',
        "gsrnamespace": 6, "gsrlimit": 50, "gsroffset": offset,
        "prop": "imageinfo", "iiprop": "url|size|mime|extmetadata",
        "iiurlwidth": 480
    }
    r = requests.get(COMMONS_API, params=params, headers=HEADERS, timeout=30)
    r.raise_for_status()
    return r.json().get("query", {}).get("pages", {}).values()

def is_allowed_video(page):
    info = (page.get("imageinfo") or [{}])[0]
    url = info.get("url", "")
    mime = info.get("mime", "")
    title = page.get("title", "")
    if not url or not (mime.startswith("video/") or re.search(r"\.(mp4|webm|ogv)(?:$|\?)", url, re.I)):
        return False
    if info.get("size", 0) > 80 * 1024 * 1024:
        return False
    return True

def safe_name(title, index, url):
    name = title.split(":", 1)[-1]
    name = re.sub(r"[^A-Za-z0-9._-]+", "_", name).strip("._")
    ext = Path(url.split("?", 1)[0]).suffix.lower()
    if ext not in (".mp4", ".webm", ".ogv"):
        ext = ".mp4"
    return f"{index:04d}_{(name or 'video')[:90]}{ext}"

@app.get("/")
def index():
    return render_template("index.html")

@app.get("/api/status")
def status():
    return jsonify({"ok": True, "source": "Wikimedia Commons", "note": "Only openly licensed files are considered; results and vertical orientation vary."})

@app.post("/api/build")
def build():
    try:
        count = max(1, min(int(request.json.get("count", 1000)), 1000))
    except Exception:
        count = 1000
    zip_path = OUT_DIR / f"memevault_{int(time.time())}.zip"
    seen = set()
    entries = []
    errors = 0
    # Commons is an open media repository. Search returns eligible video files;
    # not every result is vertical or a meme, so the archive includes source notes.
    try:
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED, compresslevel=2) as zf:
            zf.writestr("README.txt",
                "MemeVault open-media collection\n"
                "Files are sourced from Wikimedia Commons. Review each file's license and attribution.\n"
                "Note: source search results are not guaranteed to be vertical, memes, or MP4; video formats may vary.\n"
                "For phone compatibility, MP4/H.264 is preferred. This tool does not re-encode video.\n")
            idx = 0
            for term in SEARCH_TERMS:
                offset = 0
                for _ in range(4):
                    if idx >= count:
                        break
                    try:
                        pages = list(commons_search(term, offset))
                    except Exception:
                        errors += 1
                        break
                    if not pages:
                        break
                    offset += 50
                    for page in pages:
                        if idx >= count:
                            break
                        if page.get("title") in seen or not is_allowed_video(page):
                            continue
                        seen.add(page.get("title"))
                        info = (page.get("imageinfo") or [{}])[0]
                        url = info.get("url")
                        try:
                            # Stream, cap individual file size, and skip broken or huge files.
                            with requests.get(url, headers=HEADERS, stream=True, timeout=(15, 45)) as resp:
                                resp.raise_for_status()
                                length = int(resp.headers.get("content-length", "0") or 0)
                                if length and length > 80 * 1024 * 1024:
                                    continue
                                buf = io.BytesIO()
                                total = 0
                                for chunk in resp.iter_content(1024 * 256):
                                    if not chunk:
                                        continue
                                    total += len(chunk)
                                    if total > 80 * 1024 * 1024:
                                        break
                                    buf.write(chunk)
                                if total == 0 or total > 80 * 1024 * 1024:
                                    continue
                            idx += 1
                            zf.writestr(safe_name(page.get("title", "video"), idx, url), buf.getvalue())
                            source = info.get("descriptionurl", "https://commons.wikimedia.org/")
                            ext = info.get("extmetadata", {})
                            license_name = ext.get("LicenseShortName", {}).get("value", "See Commons file page")
                            entries.append(f'{idx}. {page.get("title")} | {license_name} | {source}')
                        except Exception:
                            errors += 1
                if idx >= count:
                    break
            zf.writestr("SOURCES_AND_LICENSES.txt", "\n".join(entries) if entries else
                        "No downloadable videos were found. Try again later or reduce expectations.")
    except Exception as exc:
        return jsonify({"error": f"Archive creation failed: {exc}"}), 500
    if not zip_path.exists() or zip_path.stat().st_size < 100:
        return jsonify({"error": "No usable videos were found from the open source on this run. Please retry."}), 502
    return send_file(zip_path, as_attachment=True, download_name="MemeVault_open_videos.zip", mimetype="application/zip")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "5000")), debug=False)