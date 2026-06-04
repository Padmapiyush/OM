@echo off
set APP_DIR=%LOCALAPPDATA%\AI Mailbox Manager
cd /d "%APP_DIR%\backend"
python -m uvicorn app.main:app --host 127.0.0.1 --port 8765
