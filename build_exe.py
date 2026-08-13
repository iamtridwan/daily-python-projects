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
        print("[✓] PyInstaller is installed.")
    except ImportError:
        print("[!] PyInstaller not found. Installing via pip...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])

    # 2. Build PyInstaller Command
    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--onefile",
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

    print("\n[+] Building LANShare.exe ... This may take a moment.")
    try:
        subprocess.check_call(cmd, cwd=str(project_dir))
        print("\n[✓] Build completed successfully!")
    except subprocess.CalledProcessError as e:
        print(f"\n[❌] Build failed with exit code {e.returncode}")
        sys.exit(e.returncode)

    # 3. Create Start_LAN_Share.bat shortcut launchers (both in root and in dist/)
    dist_dir = project_dir / "dist"
    dist_dir.mkdir(exist_ok=True)

    # Launcher in main project root
    root_bat = project_dir / "Start_LAN_Share.bat"
    root_bat_content = """@echo off
title LAN Share Server
echo Starting LAN Share P2P Server...
start "" "%~dp0dist\\LANShare.exe" %*
"""
    with root_bat.open("w", encoding="utf-8") as f:
        f.write(root_bat_content)

    # Launcher directly inside dist/ folder
    dist_bat = dist_dir / "Start_LAN_Share.bat"
    dist_bat_content = """@echo off
title LAN Share Server
echo Starting LAN Share P2P Server...
start "" "%~dp0LANShare.exe" %*
"""
    with dist_bat.open("w", encoding="utf-8") as f:
        f.write(dist_bat_content)

    print("\n==================================================")
    print(f"[✓] Executable created at: {dist_dir / 'LANShare.exe'}")
    print(f"[✓] Main Launcher created at: {root_bat}")
    print(f"[✓] Dist Launcher created at: {dist_bat}")
    print("==================================================")
    print("You can now double-click 'Start_LAN_Share.bat' (in root or dist/)")
    print("or 'dist/LANShare.exe' to run LAN Share without needing Python installed!\n")


if __name__ == "__main__":
    main()
