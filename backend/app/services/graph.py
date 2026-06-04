from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from urllib.parse import quote

import httpx

GRAPH_BASE = "https://graph.microsoft.com/v1.0"
FOLDER_SELECT = "id,displayName,parentFolderId,totalItemCount,unreadItemCount,childFolderCount,isHidden"
MESSAGE_SELECT = "id,conversationId,subject,bodyPreview,from,receivedDateTime,sentDateTime,isRead,hasAttachments"


@dataclass(frozen=True)
class MailFolder:
    id: str
    display_name: str
    path: str
    parent_folder_id: str | None
    total_item_count: int
    unread_item_count: int
    child_folder_count: int
    is_hidden: bool

    def as_dict(self) -> dict:
        return {
            "id": self.id,
            "display_name": self.display_name,
            "path": self.path,
            "parent_folder_id": self.parent_folder_id,
            "total_item_count": self.total_item_count,
            "unread_item_count": self.unread_item_count,
            "child_folder_count": self.child_folder_count,
            "is_hidden": self.is_hidden,
        }


class GraphClient:
    def __init__(self, access_token: str):
        self.access_token = access_token

    async def list_messages(self, folder: str = "Inbox", top: int = 25) -> list[dict]:
        """List messages in a single Outlook folder.

        ``folder`` may be a well-known folder name (for example ``Inbox``), a
        Microsoft Graph folder id, or a hierarchical path such as
        ``Inbox/Important`` or ``System Log/Escalator``.
        """
        folder_ref, folder_path = await self._resolve_folder_ref(folder)
        messages = await self._get_messages(folder_ref, top)
        return [self._normalize(m, folder_path) for m in messages]

    async def list_messages_recursive(self, root_folder: str = "Inbox", top_per_folder: int = 25) -> list[dict]:
        """List messages from a folder and all nested child folders."""
        root = await self.resolve_folder(root_folder)
        folders = [root, *await self.list_child_folders(root.id, root.path)]
        messages: list[dict] = []
        for folder in folders:
            raw_messages = await self._get_messages(folder.id, top_per_folder)
            messages.extend(self._normalize(message, folder.path) for message in raw_messages)
        return messages

    async def list_folders(self, include_hidden: bool = False) -> list[MailFolder]:
        roots = await self._get_folder_page(f"{GRAPH_BASE}/me/mailFolders?$top=100&$select={FOLDER_SELECT}&includeHiddenFolders={str(include_hidden).lower()}")
        folders: list[MailFolder] = []
        for raw in roots:
            folder = self._folder_from_graph(raw, raw.get("displayName") or "Unnamed")
            folders.append(folder)
            folders.extend(await self.list_child_folders(folder.id, folder.path, include_hidden=include_hidden))
        return folders

    async def list_child_folders(self, folder_id: str, parent_path: str, include_hidden: bool = False) -> list[MailFolder]:
        encoded_id = quote(folder_id, safe="")
        url = f"{GRAPH_BASE}/me/mailFolders/{encoded_id}/childFolders?$top=100&$select={FOLDER_SELECT}&includeHiddenFolders={str(include_hidden).lower()}"
        children = await self._get_folder_page(url)
        folders: list[MailFolder] = []
        for raw in children:
            display_name = raw.get("displayName") or "Unnamed"
            folder = self._folder_from_graph(raw, f"{parent_path}/{display_name}")
            folders.append(folder)
            if folder.child_folder_count:
                folders.extend(await self.list_child_folders(folder.id, folder.path, include_hidden=include_hidden))
        return folders

    async def resolve_folder(self, folder: str) -> MailFolder:
        normalized = folder.strip().strip("/") or "Inbox"
        if "/" not in normalized and normalized.lower() in {"inbox", "sentitems", "sent items", "drafts", "archive", "deleteditems", "deleted items"}:
            raw = await self._get_json(f"{GRAPH_BASE}/me/mailFolders/{quote(self._well_known_name(normalized), safe='')}?$select={FOLDER_SELECT}")
            return self._folder_from_graph(raw, raw.get("displayName") or normalized)
        if "/" not in normalized:
            # Could be a Graph folder id. Try id first, then display/path search.
            try:
                raw = await self._get_json(f"{GRAPH_BASE}/me/mailFolders/{quote(normalized, safe='')}?$select={FOLDER_SELECT}")
                return self._folder_from_graph(raw, raw.get("displayName") or normalized)
            except httpx.HTTPStatusError:
                pass
        folders = await self.list_folders(include_hidden=False)
        target = normalized.casefold()
        for candidate in folders:
            if candidate.path.casefold() == target or candidate.display_name.casefold() == target or candidate.id == normalized:
                return candidate
        raise ValueError(f"Outlook folder not found: {folder}")

    async def _resolve_folder_ref(self, folder: str) -> tuple[str, str]:
        resolved = await self.resolve_folder(folder)
        return resolved.id, resolved.path

    async def _get_messages(self, folder_id: str, top: int) -> list[dict]:
        encoded_id = quote(folder_id, safe="")
        url = f"{GRAPH_BASE}/me/mailFolders/{encoded_id}/messages?$top={top}&$select={MESSAGE_SELECT}"
        return await self._get_paged_values(url)

    async def _get_folder_page(self, url: str) -> list[dict]:
        return await self._get_paged_values(url)

    async def _get_paged_values(self, url: str) -> list[dict]:
        values: list[dict] = []
        while url:
            data = await self._get_json(url)
            values.extend(data.get("value", []))
            url = data.get("@odata.nextLink")
        return values

    async def _get_json(self, url: str) -> dict:
        headers = {"Authorization": f"Bearer {self.access_token}"}
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            return response.json()

    def _normalize(self, msg: dict, folder_path: str) -> dict:
        sender = (((msg.get("from") or {}).get("emailAddress") or {}).get("address"))
        return {
            "graph_id": msg["id"],
            "conversation_id": msg.get("conversationId"),
            "folder": folder_path,
            "sender": sender,
            "subject": msg.get("subject") or "",
            "body_preview": msg.get("bodyPreview"),
            "attachments": [{"hasAttachments": msg.get("hasAttachments", False)}],
            "received_at": self._dt(msg.get("receivedDateTime")),
            "sent_at": self._dt(msg.get("sentDateTime")),
            "is_read": msg.get("isRead", False),
        }

    @staticmethod
    def _folder_from_graph(raw: dict, path: str) -> MailFolder:
        return MailFolder(
            id=raw["id"],
            display_name=raw.get("displayName") or "Unnamed",
            path=path,
            parent_folder_id=raw.get("parentFolderId"),
            total_item_count=raw.get("totalItemCount") or 0,
            unread_item_count=raw.get("unreadItemCount") or 0,
            child_folder_count=raw.get("childFolderCount") or 0,
            is_hidden=raw.get("isHidden") or False,
        )

    @staticmethod
    def _well_known_name(folder: str) -> str:
        aliases = {"sent items": "sentitems", "deleted items": "deleteditems"}
        return aliases.get(folder.casefold(), folder)

    @staticmethod
    def _dt(value: str | None):
        return datetime.fromisoformat(value.replace("Z", "+00:00")).replace(tzinfo=None) if value else None
