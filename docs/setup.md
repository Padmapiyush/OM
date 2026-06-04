# Setup Guide

## Prerequisites

- Windows 10/11 with Outlook Desktop.
- Python 3.11+.
- Node.js 20+.
- Ollama installed locally with at least one supported model: `llama3`, `qwen`, or `mistral`.

## Backend

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e .[test]
uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8765
```

## Frontend

```powershell
cd frontend
npm install
npm run dev
```

## Outlook sideload

Use `manifests/outlook-addin.xml` with Outlook's add-in sideload flow. The manifest points to the local HTTPS frontend and the frontend calls the local FastAPI service at `127.0.0.1:8765`.
