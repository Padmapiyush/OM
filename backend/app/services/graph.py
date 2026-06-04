from datetime import datetime
import httpx

GRAPH_BASE = "https://graph.microsoft.com/v1.0"


class GraphClient:
    def __init__(self, access_token: str):
        self.access_token = access_token

    async def list_messages(self, folder: str = "Inbox", top: int = 25) -> list[dict]:
        headers = {"Authorization": f"Bearer {self.access_token}"}
        url = f"{GRAPH_BASE}/me/mailFolders/{folder}/messages?$top={top}&$select=id,conversationId,subject,bodyPreview,from,receivedDateTime,sentDateTime,isRead,hasAttachments"
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            return [self._normalize(m, folder) for m in response.json().get("value", [])]

    def _normalize(self, msg: dict, folder: str) -> dict:
        sender = (((msg.get("from") or {}).get("emailAddress") or {}).get("address"))
        return {
            "graph_id": msg["id"],
            "conversation_id": msg.get("conversationId"),
            "folder": folder,
            "sender": sender,
            "subject": msg.get("subject") or "",
            "body_preview": msg.get("bodyPreview"),
            "attachments": [{"hasAttachments": msg.get("hasAttachments", False)}],
            "received_at": self._dt(msg.get("receivedDateTime")),
            "sent_at": self._dt(msg.get("sentDateTime")),
            "is_read": msg.get("isRead", False),
        }

    @staticmethod
    def _dt(value: str | None):
        return datetime.fromisoformat(value.replace("Z", "+00:00")).replace(tzinfo=None) if value else None
