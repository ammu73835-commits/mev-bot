@echo off
title MEV Bot - Live Status
cd /d "%~dp0"
python CLOUD_STATUS.py --pause
