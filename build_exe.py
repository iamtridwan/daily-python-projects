"""
Build Automation Script for LAN Share Peer-to-Peer.

Packages lanshare_peer_to_peer.py into a standalone LANShare.exe
using PyInstaller and creates a 1-click Start_LAN_Share.bat launcher.
"""

import os
import subprocess
import sys
from pathlib import Path


def main():
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass

    project_dir = Path(__file__).parent.resolve()
    target_script = project_dir / "lanshare_peer_to_peer.py"

    if not target_script.exists():
        print(f"Error: {target_script} not found.")
        sys.exit(1)

    print("==================================================")
    print("      LAN Share Executable Builder (PyInstaller)  ")
    print("==================================================")

    # 1. Check if PyInstaller is installed
    try:
        import PyInstaller
        print("[OK] PyInstaller is installed.")
    except ImportError:
        print("[!] PyInstaller not found. Installing via pip...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])

    # 2. Build PyInstaller Command for Instant Directory Bundle (Starts in <0.5 seconds)
    print("\n[+] Building Instant-Launch LANShare folder (dist/LANShare) ...")
    cmd_dir = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--onedir",
        "--noconfirm",
        "--console",
        "--name",
        "LANShare",
        "--clean",
        "--hidden-import", "uvicorn.logging",
        "--hidden-import", "uvicorn.loops",
        "--hidden-import", "uvicorn.loops.auto",
        "--hidden-import", "uvicorn.protocols",
        "--hidden-import", "uvicorn.protocols.http",
        "--hidden-import", "uvicorn.protocols.http.h11_impl",
        "--hidden-import", "uvicorn.lifespan.on",
        str(target_script)
    ]

    try:
        subprocess.check_call(cmd_dir, cwd=str(project_dir))
        print("[OK] Instant-launch directory bundle created successfully!")
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] Directory build failed with exit code {e.returncode}")
        sys.exit(e.returncode)

    # 3. Build Portable Single-File Executable
    print("\n[+] Building Portable Single-File LANShare-Portable.exe ...")
    cmd_file = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--onefile",
        "--noconfirm",
        "--console",
        "--name",
        "LANShare-Portable",
        "--clean",
        "--hidden-import", "uvicorn.logging",
        "--hidden-import", "uvicorn.loops",
        "--hidden-import", "uvicorn.loops.auto",
        "--hidden-import", "uvicorn.protocols",
        "--hidden-import", "uvicorn.protocols.http",
        "--hidden-import", "uvicorn.protocols.http.h11_impl",
        "--hidden-import", "uvicorn.lifespan.on",
        str(target_script)
    ]

    try:
        subprocess.check_call(cmd_file, cwd=str(project_dir))
        print("[OK] Portable single-file executable created successfully!")
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] Portable build failed with exit code {e.returncode}")
        sys.exit(e.returncode)

    # 4. Create Start_LAN_Share.bat shortcut launchers
    dist_dir = project_dir / "dist"
    dist_dir.mkdir(exist_ok=True)

    # Launcher in main project root pointing to fast directory build
    root_bat = project_dir / "Start_LAN_Share.bat"
    root_bat_content = """@echo off
title LAN Share Server
echo Starting LAN Share P2P Server...
start "" "%~dp0dist\\LANShare\\LANShare.exe" %*
"""
    with root_bat.open("w", encoding="utf-8") as f:
        f.write(root_bat_content)

    # Launcher directly inside dist/ folder
    dist_bat = dist_dir / "Start_LAN_Share.bat"
    dist_bat_content = """@echo off
title LAN Share Server
echo Starting LAN Share P2P Server...
start "" "%~dp0LANShare\\LANShare.exe" %*
"""
    with dist_bat.open("w", encoding="utf-8") as f:
        f.write(dist_bat_content)

    print("\n==================================================")
    print(f"[OK] Instant-Launch App: {dist_dir / 'LANShare' / 'LANShare.exe'}")
    print(f"[OK] Portable Single File: {dist_dir / 'LANShare-Portable.exe'}")
    print(f"[OK] 1-Click Fast Launcher: {root_bat}")
    print("==================================================")
    print("Tip: Double-clicking 'Start_LAN_Share.bat' or 'dist/LANShare/LANShare.exe'")
    print("launches INSTANTLY without the 5-10 second unpacking delay!\n")


if __name__ == "__main__":
    main()
