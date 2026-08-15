"""
LAN Share Peer-to-Peer - WiFi File Sharing with PIN Protection & Two-Way Sharing.

Start the server on your laptop. It prints a random 4-digit PIN, a URL,
and a QR code in the terminal. Any device on the same WiFi opens the URL,
enters the PIN, and gains access to upload, download, delete files, share text, and download ZIP archives.

Features:
- 4-Digit PIN Security (regenerated per run) with signed session cookies.
- Real-Time Auto-Refresh across all connected devices via Server-Sent Events (SSE).
- Batch "Download All as ZIP" archive download.
- Quick Text & Clipboard Sharing (links, passwords, notes across LAN).
- Visual Image Thumbnails & File Type Category Icons.
- Drag-and-drop file upload with live progress bar.
- Two-way sharing gallery: view, download, or delete any file.
- Automatic host browser launch on server start.
- Single-file implementation (FastAPI, uvicorn, itsdangerous, qrcode, rich).

Run:
    python lanshare_peer_to_peer.py
    python lanshare_peer_to_peer.py ~/Downloads
    python lanshare_peer_to_peer.py ~/photos --port 9000
"""

import argparse
import asyncio
import html
import io
import json
import random
import secrets
import socket
import sys
import threading
import webbrowser
import zipfile
from datetime import datetime
from pathlib import Path
from typing import List, Optional

import qrcode
import uvicorn
from fastapi import FastAPI, File, Form, Request, UploadFile, status
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse, StreamingResponse
from itsdangerous import BadSignature, URLSafeSerializer
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

console = Console()

# Generate random 4-digit PIN and secret key per server run
SERVER_PIN = f"{random.randint(0, 9999):04d}"
SECRET_KEY = secrets.token_hex(16)
serializer = URLSafeSerializer(SECRET_KEY, salt="lanshare-session")


# ---------------------------------------------------------------------------
# REAL-TIME SSE BROADCASTER
# ---------------------------------------------------------------------------

class EventBroadcaster:
    """Broadcasts real-time events to all connected clients via SSE."""
    def __init__(self):
        self.listeners: set = set()

    async def subscribe(self):
        queue: asyncio.Queue = asyncio.Queue()
        self.listeners.add(queue)
        try:
            while True:
                message = await queue.get()
                yield f"data: {message}\n\n"
        except (asyncio.CancelledError, Exception):
            pass
        finally:
            self.listeners.discard(queue)

    def notify(self, message: str = "reload") -> None:
        for queue in list(self.listeners):
            try:
                queue.put_nowait(message)
            except Exception:
                pass


broadcaster = EventBroadcaster()


# ---------------------------------------------------------------------------
# NETWORK HELPERS
# ---------------------------------------------------------------------------

def get_lan_ip() -> str:
    """Find the local network IP address of this device."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        s.close()


# ---------------------------------------------------------------------------
# FILE & TEXT UTILITIES
# ---------------------------------------------------------------------------

def safe_filename(name: str) -> str:
    """Sanitize submitted filename to prevent directory traversal attacks."""
    name = Path(name or "").name.strip()
    if not name or name in {".", ".."}:
        return "upload"
    return name


def unique_path(folder: Path, name: str) -> Path:
    """Return folder/name, or folder/name (1), (2), ... if file exists."""
    p = folder / name
    if not p.exists():
        return p
    stem, suffix = p.stem, p.suffix
    for i in range(1, 10_000):
        candidate = folder / f"{stem} ({i}){suffix}"
        if not candidate.exists():
            return candidate
    return folder / f"{stem}-{datetime.now():%Y%m%d-%H%M%S}{suffix}"


def format_size(n: int) -> str:
    """Human-readable byte count."""
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024 or unit == "GB":
            return f"{n:.1f} {unit}" if unit != "B" else f"{n} B"
        n /= 1024
    return f"{n:.1f} TB"


def get_file_type_info(filename: str) -> dict:
    """Classify file type and return category & emoji icon."""
    ext = Path(filename).suffix.lower()
    if ext in {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".bmp"}:
        return {"type": "image", "icon": "🖼️"}
    elif ext in {".mp4", ".mov", ".webm", ".mkv", ".avi", ".m4v"}:
        return {"type": "video", "icon": "🎬"}
    elif ext in {".mp3", ".wav", ".aac", ".flac", ".ogg", ".m4a"}:
        return {"type": "audio", "icon": "🎵"}
    elif ext in {".py", ".js", ".html", ".css", ".json", ".cpp", ".c", ".java", ".ts", ".sh"}:
        return {"type": "code", "icon": "💻"}
    elif ext in {".zip", ".tar", ".gz", ".rar", ".7z"}:
        return {"type": "archive", "icon": "📦"}
    elif ext in {".pdf", ".doc", ".docx", ".txt", ".csv", ".xlsx", ".md"}:
        return {"type": "document", "icon": "📄"}
    return {"type": "other", "icon": "📁"}


def get_shared_text(upload_dir: Path) -> dict:
    """Retrieve shared text snippet data from storage."""
    file_path = upload_dir / ".shared_text.json"
    if file_path.exists():
        try:
            with file_path.open("r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"text": "", "time": "", "client": ""}


def save_shared_text(upload_dir: Path, text: str, client: str) -> dict:
    """Persist shared text snippet data to storage."""
    file_path = upload_dir / ".shared_text.json"
    data = {
        "text": text,
        "time": datetime.now().strftime("%b %d, %H:%M"),
        "client": client
    }
    try:
        with file_path.open("w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass
    return data


# ---------------------------------------------------------------------------
# AUTHENTICATION HELPERS
# ---------------------------------------------------------------------------

def is_authenticated(request: Request) -> bool:
    """Check if request contains a valid signed session cookie."""
    cookie = request.cookies.get("lanshare_session")
    if not cookie:
        return False
    try:
        data = serializer.loads(cookie)
        return isinstance(data, dict) and data.get("auth") is True
    except BadSignature:
        return False


# ---------------------------------------------------------------------------
# HTML TEMPLATES (Inline Pico.css)
# ---------------------------------------------------------------------------

PAGE_LOGIN = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>LAN Share - Unlock</title>
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/@picocss/pico@2/css/pico.min.css">
  <style>
    body {{
      padding-top: 4rem;
      display: flex;
      justify-content: center;
      background-color: #ffffff;
    }}
    main {{
      width: 100%;
      max-width: 400px;
      padding: 1rem;
    }}
    .header-box {{
      text-align: center;
      margin-bottom: 2rem;
    }}
    .header-box h1 {{
      font-size: 1.8rem;
      margin-bottom: 0.5rem;
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 0.5rem;
    }}
    .header-box p {{
      color: var(--pico-muted-color);
      font-size: 0.95rem;
      margin: 0;
    }}
    input[type="text"] {{
      text-align: center;
      letter-spacing: 0.25rem;
      font-size: 1.2rem;
      margin-bottom: 1rem;
    }}
    .error-banner {{
      background-color: #fee2e2;
      color: #991b1b;
      padding: 0.75rem 1rem;
      border-radius: 8px;
      margin-bottom: 1rem;
      text-align: center;
      font-size: 0.9rem;
    }}
    button {{
      font-weight: bold;
    }}
  </style>
</head>
<body>
<main>
  <div class="header-box">
    <h1>🔒 LAN Share</h1>
    <p>Enter the 4-digit PIN shown on the host's terminal.</p>
  </div>
  {error_banner}
  <form method="post" action="/login">
    <input type="text" name="pin" maxlength="4" pattern="[0-9]{{4}}" placeholder="" required autofocus autocomplete="off">
    <button type="submit">Unlock</button>
  </form>
</main>
</body>
</html>
"""

PAGE_MAIN = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>LAN Share</title>
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/@picocss/pico@2/css/pico.min.css">
  <style>
    body {{ padding-top: 2rem; background-color: #ffffff; }}
    main {{ max-width: 520px; margin: 0 auto; padding: 0 1rem; }}
    .header-row {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 0.25rem;
    }}
    .header-row h1 {{
      font-size: 1.8rem;
      margin: 0;
      display: flex;
      align-items: center;
      gap: 0.5rem;
    }}
    .header-row a.lock-link {{
      color: var(--pico-muted-color);
      text-decoration: none;
      font-size: 0.95rem;
    }}
    .header-row a.lock-link:hover {{ text-decoration: underline; }}
    .subtitle {{
      color: var(--pico-muted-color);
      margin-bottom: 1.5rem;
      font-size: 0.95rem;
    }}
    .upload-box {{
      border: 2px dashed #93c5fd;
      border-radius: 12px;
      padding: 2.5rem 1rem;
      text-align: center;
      margin-bottom: 1.5rem;
      cursor: pointer;
      transition: background-color 0.2s, border-color 0.2s;
      background-color: #fafafa;
    }}
    .upload-box.dragover {{
      background-color: #eff6ff;
      border-color: #2563eb;
    }}
    .upload-icon {{
      font-size: 2rem;
      margin-bottom: 0.5rem;
      color: #64748b;
    }}
    .upload-box p {{
      margin: 0;
      line-height: 1.4;
    }}
    .progress-container {{
      margin-bottom: 1.5rem;
      text-align: center;
    }}
    .progress-text {{
      font-size: 0.9rem;
      color: var(--pico-muted-color);
      margin-top: 0.5rem;
    }}
    .text-share-card {{
      background-color: #f8fafc;
      border: 1px solid #e2e8f0;
      border-radius: 12px;
      padding: 1rem;
      margin-bottom: 1.5rem;
    }}
    .text-share-header {{
      font-weight: 600;
      font-size: 0.95rem;
      color: #334155;
      margin-bottom: 0.5rem;
    }}
    .text-share-card textarea {{
      width: 100%;
      font-size: 0.9rem;
      margin-bottom: 0.5rem;
      resize: vertical;
      border-radius: 8px;
    }}
    .text-share-actions {{
      display: flex;
      gap: 0.5rem;
    }}
    .btn-share-text {{
      background-color: #2563eb;
      border-color: #2563eb;
      color: white;
      padding: 0.35rem 0.75rem;
      font-size: 0.85rem;
      border-radius: 6px;
      margin: 0;
      cursor: pointer;
    }}
    .btn-copy-text {{
      background-color: #f1f5f9;
      border: 1px solid #cbd5e1;
      color: #334155;
      padding: 0.35rem 0.75rem;
      font-size: 0.85rem;
      border-radius: 6px;
      cursor: pointer;
      margin: 0;
    }}
    .btn-copy-text:hover {{
      background-color: #e2e8f0;
    }}
    .shared-meta-text {{
      font-size: 0.75rem;
      color: #94a3b8;
      margin-top: 0.4rem;
    }}
    .shared-display-box {{
      background-color: #ffffff;
      border: 1px solid #cbd5e1;
      border-radius: 8px;
      padding: 0.75rem 1rem;
      margin-bottom: 0.75rem;
      word-break: break-all;
    }}
    .shared-display-label {{
      font-size: 0.75rem;
      font-weight: 600;
      color: #64748b;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      margin-bottom: 0.25rem;
    }}
    .shared-display-content {{
      font-size: 0.95rem;
      color: #0f172a;
    }}
    .shared-display-content a {{
      color: #2563eb;
      font-weight: 600;
      text-decoration: underline;
    }}
    .files-header-row {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 1rem;
    }}
    .files-header {{
      font-size: 1.3rem;
      font-weight: bold;
      margin: 0;
    }}
    .files-header span {{
      color: var(--pico-muted-color);
      font-weight: normal;
    }}
    .btn-download-all {{
      background-color: #0f172a;
      border-color: #0f172a;
      color: white;
      padding: 0.35rem 0.75rem;
      font-size: 0.85rem;
      border-radius: 6px;
      text-decoration: none;
      display: inline-block;
      line-height: 1.2;
    }}
    .btn-download-all:hover {{
      background-color: #1e293b;
    }}
    .file-card {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 0.85rem 0;
      border-bottom: 1px solid #f1f5f9;
    }}
    .file-left {{
      display: flex;
      align-items: center;
      gap: 0.85rem;
      overflow: hidden;
      padding-right: 0.5rem;
    }}
    .file-thumb {{
      width: 48px;
      height: 48px;
      border-radius: 8px;
      overflow: hidden;
      background-color: #f1f5f9;
      display: flex;
      align-items: center;
      justify-content: center;
      flex-shrink: 0;
      border: 1px solid #e2e8f0;
    }}
    .thumb-img {{
      width: 100%;
      height: 100%;
      object-fit: cover;
    }}
    .thumb-icon {{
      font-size: 1.5rem;
    }}
    .file-info {{
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }}
    .file-name {{
      font-weight: 600;
      font-size: 0.95rem;
      color: #0f172a;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }}
    .file-name a {{
      color: inherit;
      text-decoration: none;
    }}
    .file-name a:hover {{
      text-decoration: underline;
    }}
    .file-meta {{
      font-size: 0.8rem;
      color: #64748b;
      margin-top: 0.15rem;
    }}
    .file-actions {{
      display: flex;
      gap: 0.5rem;
      flex-shrink: 0;
    }}
    .btn-download {{
      background-color: #0284c7;
      border-color: #0284c7;
      color: white;
      padding: 0.35rem 0.75rem;
      font-size: 0.85rem;
      border-radius: 6px;
      text-decoration: none;
      display: inline-block;
      line-height: 1.2;
    }}
    .btn-download:hover {{
      background-color: #0369a1;
    }}
    .btn-delete {{
      background-color: transparent;
      border: 1px solid #ef4444;
      color: #ef4444;
      padding: 0.35rem 0.75rem;
      font-size: 0.85rem;
      border-radius: 6px;
      cursor: pointer;
      line-height: 1.2;
      margin: 0;
    }}
    .btn-delete:hover {{
      background-color: #fef2f2;
    }}
    .empty-state {{
      text-align: center;
      color: var(--pico-muted-color);
      padding: 2rem 0;
      font-style: italic;
    }}
  </style>
</head>
<body>
<main>
  <div class="header-row">
    <h1>📡 LAN Share</h1>
    <a href="/logout" class="lock-link">Lock</a>
  </div>
  <div class="subtitle">Serving on <strong>{host}</strong></div>

  <div class="upload-box" id="dropZone">
    <div class="upload-icon">⬆</div>
    <p><strong>Drop files here</strong> or tap to pick.</p>
    <p style="font-size: 0.85rem; color: var(--pico-muted-color);">Any file type. Uploads run in the background.</p>
    <input type="file" id="fileInput" multiple style="display: none;">
  </div>

  <div class="progress-container" id="progressContainer" style="display: none;">
    <progress id="progressBar" value="0" max="100"></progress>
    <div class="progress-text" id="progressText">Uploading... 0%</div>
  </div>

  <div class="text-share-card">
    <div class="text-share-header">📋 Quick Text & Link Share</div>
    {shared_display_html}
    <form method="post" action="/text">
      <textarea name="text" id="sharedTextInput" rows="2" placeholder="Paste a link, Wi-Fi password, or quick note...">{shared_text}</textarea>
      <div class="text-share-actions">
        <button type="submit" class="btn-share-text">Share Text</button>
        <button type="button" class="btn-copy-text" id="btnCopyText" onclick="copySharedText();">Copy Text</button>
      </div>
    </form>
    {shared_text_meta}
  </div>

  <div class="files-header-row">
    <div class="files-header">Files <span>({file_count})</span></div>
    {download_all_btn}
  </div>

  <div class="file-list">
    {file_cards}
  </div>
</main>

<script>
  const dropZone = document.getElementById('dropZone');
  const fileInput = document.getElementById('fileInput');
  const progressContainer = document.getElementById('progressContainer');
  const progressBar = document.getElementById('progressBar');
  const progressText = document.getElementById('progressText');

  dropZone.addEventListener('click', () => fileInput.click());

  dropZone.addEventListener('dragover', (e) => {{
    e.preventDefault();
    dropZone.classList.add('dragover');
  }});

  dropZone.addEventListener('dragleave', () => {{
    dropZone.classList.remove('dragover');
  }});

  dropZone.addEventListener('drop', (e) => {{
    e.preventDefault();
    dropZone.classList.remove('dragover');
    if (e.dataTransfer.files.length > 0) {{
      uploadFiles(e.dataTransfer.files);
    }}
  }});

  fileInput.addEventListener('change', () => {{
    if (fileInput.files.length > 0) {{
      uploadFiles(fileInput.files);
    }}
  }});

  function uploadFiles(files) {{
    const formData = new FormData();
    for (let i = 0; i < files.length; i++) {{
      formData.append('files', files[i]);
    }}

    progressContainer.style.display = 'block';
    progressBar.value = 0;
    progressText.innerText = `Uploading ${{files.length}} file(s)... 0%`;

    const xhr = new XMLHttpRequest();
    xhr.open('POST', '/upload', true);

    xhr.upload.onprogress = (e) => {{
      if (e.lengthComputable) {{
        const percent = Math.round((e.loaded / e.total) * 100);
        progressBar.value = percent;
        progressText.innerText = `Uploading ${{files.length}} file(s)... ${{percent}}%`;
      }}
    }};

    xhr.onload = () => {{
      if (xhr.status === 200) {{
        // Reload triggered automatically via SSE or fallback
        window.location.reload();
      }} else {{
        alert('Upload failed. Please try again.');
        progressContainer.style.display = 'none';
      }}
    }};

    xhr.onerror = () => {{
      alert('Upload failed due to network error.');
      progressContainer.style.display = 'none';
    }};

    xhr.send(formData);
  }}

  function copySharedText() {{
    const textarea = document.getElementById('sharedTextInput');
    const textToCopy = textarea ? textarea.value.trim() : '';
    if (!textToCopy) return;

    const btn = document.getElementById('btnCopyText');
    const originalText = btn ? btn.innerText : 'Copy Text';

    function showSuccess() {{
      if (btn) {{
        btn.innerText = 'Copied! ✓';
        setTimeout(() => btn.innerText = originalText, 2000);
      }}
    }}

    function fallbackCopy() {{
      try {{
        textarea.focus();
        textarea.select();
        textarea.setSelectionRange(0, 99999);
        const successful = document.execCommand('copy');
        if (successful) {{
          showSuccess();
        }} else {{
          alert('Copy failed. Please manually select and copy text.');
        }}
      }} catch (err) {{
        alert('Copy failed. Please manually select and copy text.');
      }}
    }}

    if (navigator.clipboard && typeof navigator.clipboard.writeText === 'function') {{
      navigator.clipboard.writeText(textToCopy).then(showSuccess).catch(() => fallbackCopy());
    }} else {{
      fallbackCopy();
    }}
  }}

  // Real-time Auto-Refresh via Server-Sent Events (SSE) with Fallback Polling
  let lastSharedText = undefined;
  let sseActive = false;

  if (window.EventSource) {{
    try {{
      const evtSource = new EventSource('/events');
      evtSource.onopen = () => {{ sseActive = true; }};
      evtSource.onmessage = (e) => {{
        if (e.data === 'reload') {{
          window.location.reload();
        }}
      }};
      evtSource.onerror = () => {{ sseActive = false; }};
    }} catch(err) {{
      sseActive = false;
    }}
  }}

  // Backup polling every 3 seconds to ensure real-time sync across devices even if SSE drops
  setInterval(async () => {{
    try {{
      const res = await fetch('/text');
      if (res.ok) {{
        const data = await res.json();
        if (lastSharedText === undefined) {{
          lastSharedText = data.text || '';
        }} else if (data.text !== undefined && data.text !== lastSharedText) {{
          window.location.reload();
        }}
      }}
    }} catch(e) {{}}
  }}, 3000);
</script>
</body>
</html>
"""


# ---------------------------------------------------------------------------
# FASTAPI APP CREATION
# ---------------------------------------------------------------------------

def create_app(upload_dir: Path, display_host: str) -> FastAPI:
    app = FastAPI(title="LAN Share P2P")

    @app.get("/", response_class=HTMLResponse)
    async def home(request: Request):
        if not is_authenticated(request):
            return RedirectResponse("/login", status_code=status.HTTP_303_SEE_OTHER)

        # Get shared text data
        shared_data = get_shared_text(upload_dir)
        raw_text = shared_data.get("text", "")
        escaped_text = html.escape(raw_text)

        shared_display_html = ""
        if raw_text:
            if raw_text.startswith("http://") or raw_text.startswith("https://"):
                shared_display_html = f"""
                <div class="shared-display-box">
                  <div class="shared-display-label">🔗 Active Shared Link:</div>
                  <div class="shared-display-content">
                    <a href="{escaped_text}" target="_blank" rel="noopener">{escaped_text}</a>
                  </div>
                </div>
                """
            else:
                shared_display_html = f"""
                <div class="shared-display-box">
                  <div class="shared-display-label">💬 Active Shared Text:</div>
                  <div class="shared-display-content">{escaped_text}</div>
                </div>
                """

        shared_meta = ""
        if shared_data.get("time"):
            client_ip = html.escape(shared_data.get("client", ""))
            shared_meta = f'<div class="shared-meta-text">Last shared: {shared_data["time"]} from {client_ip}</div>'

        # Get list of files sorted by modification time (newest first)
        files = []
        if upload_dir.exists():
            for p in upload_dir.iterdir():
                if p.is_file() and not p.name.startswith("."):
                    stat = p.stat()
                    type_info = get_file_type_info(p.name)
                    files.append({
                        "name": p.name,
                        "size": format_size(stat.st_size),
                        "time": datetime.fromtimestamp(stat.st_mtime).strftime("%b %d, %H:%M"),
                        "mtime": stat.st_mtime,
                        "type": type_info["type"],
                        "icon": type_info["icon"],
                    })
        files.sort(key=lambda f: f["mtime"], reverse=True)

        download_all_btn = ""
        if files:
            download_all_btn = '<a href="/download-all" class="btn-download-all">📦 Download All (.zip)</a>'

        # Build file list HTML cards
        if files:
            cards = []
            for f in files:
                # Render visual thumbnail for images, icon badge for other files
                if f["type"] == "image":
                    thumb_html = f"""
                    <a href="/download/{f['name']}" target="_blank">
                      <img src="/thumbnail/{f['name']}" alt="{f['name']}" class="thumb-img" loading="lazy">
                    </a>
                    """
                else:
                    thumb_html = f'<div class="thumb-icon">{f["icon"]}</div>'

                card = f"""
                <div class="file-card">
                  <div class="file-left">
                    <div class="file-thumb">
                      {thumb_html}
                    </div>
                    <div class="file-info">
                      <div class="file-name"><a href="/download/{f['name']}" target="_blank">{f['name']}</a></div>
                      <div class="file-meta">{f['size']} · {f['time']}</div>
                    </div>
                  </div>
                  <div class="file-actions">
                    <a href="/download/{f['name']}" class="btn-download">Download</a>
                    <form method="post" action="/delete/{f['name']}" style="margin:0;">
                      <button type="submit" class="btn-delete" onclick="return confirm('Delete {f['name']}?');">Delete</button>
                    </form>
                  </div>
                </div>
                """
                cards.append(card)
            file_cards_html = "".join(cards)
        else:
            file_cards_html = '<div class="empty-state">No files shared yet. Drop files above to start.</div>'

        return HTMLResponse(PAGE_MAIN.format(
            host=display_host,
            file_count=len(files),
            file_cards=file_cards_html,
            shared_display_html=shared_display_html,
            shared_text=escaped_text,
            shared_text_meta=shared_meta,
            download_all_btn=download_all_btn
        ))

    @app.get("/login", response_class=HTMLResponse)
    async def login_page(request: Request):
        if is_authenticated(request):
            return RedirectResponse("/", status_code=status.HTTP_303_SEE_OTHER)
        return HTMLResponse(PAGE_LOGIN.format(error_banner=""))

    @app.post("/login")
    async def login_submit(pin: str = Form(...)):
        if pin.strip() == SERVER_PIN:
            response = RedirectResponse("/", status_code=status.HTTP_303_SEE_OTHER)
            cookie_value = serializer.dumps({"auth": True})
            response.set_cookie("lanshare_session", cookie_value, httponly=True, samesite="lax")
            return response

        error_html = '<div class="error-banner">❌ Incorrect PIN. Try again.</div>'
        return HTMLResponse(PAGE_LOGIN.format(error_banner=error_html))

    @app.get("/logout")
    async def logout():
        response = RedirectResponse("/login", status_code=status.HTTP_303_SEE_OTHER)
        response.delete_cookie("lanshare_session")
        return response

    @app.get("/events")
    async def sse_events(request: Request):
        if not is_authenticated(request):
            return JSONResponse({"error": "Unauthorized"}, status_code=401)
        return StreamingResponse(
            broadcaster.subscribe(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no"
            }
        )

    @app.post("/text")
    async def share_text(request: Request, text: str = Form("")):
        if not is_authenticated(request):
            return RedirectResponse("/login", status_code=status.HTTP_303_SEE_OTHER)

        client = request.client.host if request.client else "?"
        save_shared_text(upload_dir, text.strip(), client)
        ts = datetime.now().strftime("%H:%M:%S")
        console.print(
            f"[dim]{ts}[/dim]  "
            f"[cyan]{client:>15}[/cyan]  "
            f"[yellow]shared text snippet[/yellow]"
        )
        broadcaster.notify("reload")
        return RedirectResponse("/", status_code=status.HTTP_303_SEE_OTHER)

    @app.get("/text")
    async def get_text(request: Request):
        if not is_authenticated(request):
            return JSONResponse({"error": "Unauthorized"}, status_code=401)
        return JSONResponse(get_shared_text(upload_dir))

    @app.get("/download-all")
    async def download_all(request: Request):
        if not is_authenticated(request):
            return RedirectResponse("/login", status_code=status.HTTP_303_SEE_OTHER)

        files_to_zip = []
        if upload_dir.exists():
            for p in upload_dir.iterdir():
                if p.is_file() and not p.name.startswith("."):
                    files_to_zip.append(p)

        if not files_to_zip:
            return HTMLResponse("No files available to download.", status_code=400)

        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
            for file_path in files_to_zip:
                zip_file.write(file_path, arcname=file_path.name)

        zip_buffer.seek(0)
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        filename = f"lanshare-archive-{timestamp}.zip"

        return StreamingResponse(
            zip_buffer,
            media_type="application/zip",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'}
        )

    @app.get("/thumbnail/{filename}")
    async def get_thumbnail(request: Request, filename: str):
        if not is_authenticated(request):
            return JSONResponse({"error": "Unauthorized"}, status_code=401)

        safe_name = safe_filename(filename)
        file_path = (upload_dir / safe_name).resolve()

        if not file_path.exists() or not file_path.is_file() or upload_dir.resolve() not in file_path.parents:
            return JSONResponse({"error": "File not found"}, status_code=404)

        # Check if file is image type
        type_info = get_file_type_info(safe_name)
        if type_info["type"] == "image":
            return FileResponse(file_path, headers={"Cache-Control": "max-age=3600"})

        return JSONResponse({"error": "No thumbnail available"}, status_code=400)

    @app.post("/upload")
    async def upload_files(request: Request, files: List[UploadFile] = File(...)):
        if not is_authenticated(request):
            return JSONResponse({"error": "Unauthorized"}, status_code=401)

        saved_count = 0
        for f in files:
            if not f.filename:
                continue
            name = safe_filename(f.filename)
            path = unique_path(upload_dir, name)

            size = 0
            with path.open("wb") as out:
                while True:
                    chunk = await f.read(1024 * 1024)  # Stream 1 MB chunks
                    if not chunk:
                        break
                    out.write(chunk)
                    size += len(chunk)

            saved_count += 1
            client = request.client.host if request.client else "?"
            ts = datetime.now().strftime("%H:%M:%S")
            console.print(
                f"[dim]{ts}[/dim]  "
                f"[cyan]{client:>15}[/cyan]  "
                f"[green]uploaded[/green] "
                f"[bold]{path.name}[/bold]  "
                f"[dim]({format_size(size)})[/dim]"
            )

        if saved_count > 0:
            broadcaster.notify("reload")

        return JSONResponse({"status": "ok", "uploaded": saved_count})

    @app.get("/download/{filename}")
    async def download_file(request: Request, filename: str):
        if not is_authenticated(request):
            return RedirectResponse("/login", status_code=status.HTTP_303_SEE_OTHER)

        safe_name = safe_filename(filename)
        file_path = (upload_dir / safe_name).resolve()

        if not file_path.exists() or not file_path.is_file() or upload_dir.resolve() not in file_path.parents:
            return HTMLResponse("File not found", status_code=404)

        return FileResponse(file_path, filename=safe_name, media_type="application/octet-stream")

    @app.post("/delete/{filename}")
    async def delete_file(request: Request, filename: str):
        if not is_authenticated(request):
            return RedirectResponse("/login", status_code=status.HTTP_303_SEE_OTHER)

        safe_name = safe_filename(filename)
        file_path = (upload_dir / safe_name).resolve()

        if file_path.exists() and file_path.is_file() and upload_dir.resolve() in file_path.parents:
            file_path.unlink()
            ts = datetime.now().strftime("%H:%M:%S")
            console.print(
                f"[dim]{ts}[/dim]  "
                f"[red]deleted[/red] "
                f"[bold]{safe_name}[/bold]"
            )
            broadcaster.notify("reload")

        return RedirectResponse("/", status_code=status.HTTP_303_SEE_OTHER)

    return app


# ---------------------------------------------------------------------------
# TERMINAL BANNER & CLI
# ---------------------------------------------------------------------------

def print_startup_banner(url: str, upload_dir: Path, pin: str) -> None:
    """Print colored terminal banner with PIN, URL, and QR code."""
    text = Text()
    text.append("Open on any device on the same WiFi:\n\n", style="bold")
    text.append(f"   {url}\n\n", style="bold cyan")
    text.append("Enter 4-digit PIN when prompted:\n\n", style="bold")
    text.append(f"   🔑 PIN: {pin}\n\n", style="bold yellow")
    text.append(f"Files land in: {upload_dir}\n", style="dim")
    text.append("Press Ctrl+C to stop.", style="dim")

    console.print()
    console.print(Panel(text, title="[bold]\U0001F4E1 LAN Share (Peer-to-Peer)[/bold]",
                        border_style="cyan", padding=(1, 2)))
    console.print()

    # Generate ASCII QR Code for rapid mobile scanning
    qr = qrcode.QRCode(border=1)
    qr.add_data(url)
    qr.make(fit=True)
    qr.print_ascii(invert=True)

    console.print()
    console.print("[dim]" + "-" * 45 + "[/dim]")
    console.print("[dim]Server logs:[/dim]\n")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Serve a two-way peer-to-peer file sharing page over local WiFi.",
    )
    parser.add_argument(
        "folder",
        nargs="?",
        default="~/lanshare",
        help="Directory to save uploads to (default: ~/lanshare).",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port to listen on (default: 8000).",
    )
    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="Bind address (default: 0.0.0.0 - all interfaces).",
    )
    parser.add_argument(
        "--no-browser",
        action="store_true",
        help="Do not auto-open the web browser on startup.",
    )
    args = parser.parse_args()

    upload_dir = Path(args.folder).expanduser().resolve()
    upload_dir.mkdir(parents=True, exist_ok=True)

    lan_ip = get_lan_ip()
    if lan_ip == "127.0.0.1":
        console.print("[yellow]Warning:[/yellow] no LAN network detected. "
                      "Starting on localhost.")

    display_host = f"{lan_ip}:{args.port}"
    url = f"http://{display_host}"

    print_startup_banner(url, upload_dir, SERVER_PIN)

    # Launch browser automatically on laptop host unless --no-browser is passed
    if not args.no_browser:
        def open_browser():
            try:
                webbrowser.open(f"http://127.0.0.1:{args.port}")
            except Exception:
                pass
        threading.Timer(1.2, open_browser).start()

    app = create_app(upload_dir, display_host)

    config = uvicorn.Config(app=app, host=args.host, port=args.port, log_level="warning")
    server = uvicorn.Server(config)
    server.install_signal_handlers = lambda: None

    try:
        server.run()
    except (KeyboardInterrupt, SystemExit):
        pass
    except Exception as e:
        console.print(f"\n[red]Server error:[/red] {e}")
    finally:
        console.print("\n[bold cyan]LAN Share server stopped cleanly.[/bold cyan]")
        sys.exit(0)


if __name__ == "__main__":
    main()
