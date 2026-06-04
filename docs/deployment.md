# Deployment Guide

## Local desktop package

1. Build the backend environment inside the installer staging directory.
2. Build the task pane with `npm run build` from `frontend`.
3. Compile `installer/ai-mailbox-manager.iss` with Inno Setup.
4. Install Ollama and pull a local model: `ollama pull llama3`.
5. Sideload or centrally deploy the Outlook manifest to users.

## Privacy controls

- SQLite database path defaults to `%LOCALAPPDATA%\AI Mailbox Manager\mailbox.db`.
- No telemetry endpoint is implemented.
- Microsoft Graph is called only with a token supplied by Outlook/user context.
- OpenAI fallback is disabled unless `ENABLE_OPENAI=true` and an API key are explicitly set.

## Operations

Run the local API:

```powershell
python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8765
```

Health check: `http://127.0.0.1:8765/health`.
