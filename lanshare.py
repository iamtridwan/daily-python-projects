"""
LAN Share - Day 1: file uploads from any device on your WiFi.

You start the server on your laptop. It prints a QR code and a URL. Any
device on the same WiFi (your phone, your friend's Android, your kid's
iPad, another laptop) scans the QR or types the URL, picks files from
their file / photo picker, hits Upload, and the files land in a folder
on your laptop.

No accounts. No cloud. No Apple ecosystem. No 25 MB email attachment
limit. Just plain HTTP over your LAN.

Everything - server, HTML, upload logic - lives in this ONE file.
Templates are inlined as strings; CSS comes from a CDN (Pico.css).

Run:
    pip install fastapi uvicorn python-multipart qrcode rich
    python lanshare.py
    python lanshare.py ~/Downloads          # save uploads there
    python lanshare.py ~/photos --port 9000
"""

import argparse
import socket
import sys
from datetime import datetime
from pathlib import Path
from typing import List

import qrcode
# pyrefly: ignore [missing-import]
import uvicorn
# pyrefly: ignore [missing-import]
from fastapi import FastAPI, File, Request, UploadFile
# pyrefly: ignore [missing-import]
from fastapi.responses import HTMLResponse, RedirectResponse
# pyrefly: ignore [missing-import]
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

console = Console()


# ---------------------------------------------------------------------------
# NETWORK - find the IP the LAN can reach us at
# ---------------------------------------------------------------------------

def get_lan_ip() -> str:
    """Find the LAN IP other devices on the network can reach us at.

    Trick: open a UDP socket and 'connect' it to a public IP (Google DNS).
    UDP is connectionless so no packets are actually sent, but the kernel
    picks the outbound network interface and its IP - which is exactly
    the IP other devices on our LAN should point at.
    """
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    except OSError:
        return "127.0.0.1"       # not connected to any network
    finally:
        s.close()


# ---------------------------------------------------------------------------
# FILENAME SAFETY
# ---------------------------------------------------------------------------

def safe_filename(name: str) -> str:
    """Reduce a submitted filename to a safe basename.

    Strips any path components (protects against ../../etc/passwd attacks
    from a malicious client crafting the filename in a multipart upload)
    and falls back to 'upload' if the result is empty.
    """
    name = Path(name or "").name.strip()
    if not name or name in {".", ".."}:
        return "upload"
    return name


def unique_path(folder: Path, name: str) -> Path:
    """Return folder/name, or folder/name (1), (2), ... if it exists."""
    p = folder / name
    if not p.exists():
        return p
    stem, suffix = p.stem, p.suffix
    for i in range(1, 10_000):
        candidate = folder / f"{stem} ({i}){suffix}"
        if not candidate.exists():
            return candidate
    # Give up gracefully after 10k collisions - append a timestamp.
    return folder / f"{stem}-{datetime.now():%Y%m%d-%H%M%S}{suffix}"


# ---------------------------------------------------------------------------
# FORMATTING
# ---------------------------------------------------------------------------

def format_size(n: int) -> str:
    """Human-readable byte count."""
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024 or unit == "GB":
            return f"{n:.1f} {unit}" if unit != "B" else f"{n} B"
        n /= 1024
    return f"{n:.1f} TB"


# ---------------------------------------------------------------------------
# HTML - a single inline template
# ---------------------------------------------------------------------------

PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>LAN Share</title>
  <link rel="stylesheet"
        href="https://cdn.jsdelivr.net/npm/@picocss/pico@2/css/pico.min.css">
  <style>
    body {{ padding-top: 2rem; }}
    .upload-box {{
      border: 2px dashed var(--pico-muted-border-color);
      border-radius: 12px;
      padding: 2rem 1rem;
      text-align: center;
      margin-bottom: 1rem;
    }}
    .upload-box input[type=file] {{
      margin: 0 auto;
      display: block;
    }}
    .banner {{
      background: #d1fae5;
      color: #065f46;
      padding: 0.75rem 1rem;
      border-radius: 8px;
      margin-bottom: 1rem;
    }}
  </style>
</head>
<body>
<main class="container">
  <hgroup>
    <h1>&#128225; LAN Share</h1>
    <p>Uploading to <strong>{host}</strong></p>
  </hgroup>

  {banner}

  <form method="post" action="/upload" enctype="multipart/form-data">
    <div class="upload-box">
      <p style="margin-bottom:0.5rem">
        <strong>Pick files to upload</strong><br>
        <small>Tap to open your photo library, files, or camera.</small>
      </p>
      <input type="file" name="files" multiple required>
    </div>
    <button type="submit">Upload</button>
  </form>

  <footer style="margin-top:3rem; color:var(--pico-muted-color);
                 font-size:0.85em; text-align:center">
    Serving over your local WiFi. No cloud, no accounts.
  </footer>
</main>
</body>
</html>
"""


def render_page(host: str, banner: str = "") -> str:
    return PAGE.format(host=host, banner=banner)


# ---------------------------------------------------------------------------
# FASTAPI APP
# ---------------------------------------------------------------------------

def create_app(upload_dir: Path, display_host: str) -> FastAPI:
    app = FastAPI(title="LAN Share")

    @app.get("/", response_class=HTMLResponse)
    async def home(uploaded: int = 0):
        banner = ""
        if uploaded > 0:
            plural = "s" if uploaded != 1 else ""
            banner = (f'<div class="banner">'
                      f'&#9989; Uploaded {uploaded} file{plural}. '
                      f'Ready for more.'
                      f'</div>')
        return HTMLResponse(render_page(display_host, banner))

    @app.post("/upload")
    async def upload(request: Request,
                     files: List[UploadFile] = File(...)):
        client = request.client.host if request.client else "?"
        saved_count = 0

        for f in files:
            if not f.filename:
                continue     # empty picker entry
            name = safe_filename(f.filename)
            path = unique_path(upload_dir, name)

            # Stream to disk in 1 MB chunks - never load whole file in RAM.
            # A 4 GB video would happily upload with this loop.
            size = 0
            with path.open("wb") as out:
                while True:
                    chunk = await f.read(1024 * 1024)
                    if not chunk:
                        break
                    out.write(chunk)
                    size += len(chunk)

            saved_count += 1
            ts = datetime.now().strftime("%H:%M:%S")
            console.print(
                f"[dim]{ts}[/dim]  "
                f"[cyan]{client:>15}[/cyan]  "
                f"[green]uploaded[/green] "
                f"[bold]{path.name}[/bold]  "
                f"[dim]({format_size(size)})[/dim]"
            )

        return RedirectResponse(f"/?uploaded={saved_count}", status_code=303)

    return app


# ---------------------------------------------------------------------------
# TERMINAL BANNER + QR
# ---------------------------------------------------------------------------

def print_startup_banner(url: str, upload_dir: Path) -> None:
    """Print a big colored startup banner with URL, folder, and QR."""
    text = Text()
    text.append("Open on any device on the same WiFi:\n\n", style="bold")
    text.append(f"   {url}\n\n", style="bold cyan")
    text.append("Or scan the QR code below.\n\n", style="dim")
    text.append(f"Files land in: {upload_dir}\n", style="dim")
    text.append("Press Ctrl+C to stop.", style="dim")

    console.print()
    console.print(Panel(text, title="[bold]\U0001F4E1 LAN Share[/bold]",
                        border_style="cyan", padding=(1, 2)))
    console.print()

    # QR code straight to stdout - qrcode uses half-block Unicode chars,
    # so the whole thing fits in 33 columns.
    qr = qrcode.QRCode(border=1)
    qr.add_data(url)
    qr.make(fit=True)
    qr.print_ascii(invert=True)

    console.print()
    console.print("[dim]" + "-" * 40 + "[/dim]")
    console.print("[dim]Uploads:[/dim]\n")


# ---------------------------------------------------------------------------
# ENTRY POINT
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Serve a file upload page over your local WiFi.",
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
    args = parser.parse_args()

    upload_dir = Path(args.folder).expanduser().resolve()
    upload_dir.mkdir(parents=True, exist_ok=True)

    lan_ip = get_lan_ip()
    if lan_ip == "127.0.0.1":
        console.print("[yellow]Warning:[/yellow] no LAN network detected. "
                      "The server will still start on localhost, but no "
                      "other device will be able to reach it.")

    url = f"http://{lan_ip}:{args.port}"
    print_startup_banner(url, upload_dir)

    app = create_app(upload_dir, f"{lan_ip}:{args.port}")

    try:
        uvicorn.run(app, host=args.host, port=args.port, log_level="warning")
    except KeyboardInterrupt:
        console.print("\n[dim]Stopped.[/dim]")
        sys.exit(0)


if __name__ == "__main__":
    main()