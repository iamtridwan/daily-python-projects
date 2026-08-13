@echo off
title LAN Share Server
echo Starting LAN Share P2P Server...
start "" "%~dp0dist\LANShare.exe" %*
