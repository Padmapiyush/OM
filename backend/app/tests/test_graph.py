import pytest

from app.services.graph import GraphClient


class FakeGraphClient(GraphClient):
    def __init__(self):
        super().__init__("token")
        self.children = {
            "root": [{"id": "child", "displayName": "Important", "parentFolderId": "root", "childFolderCount": 0, "totalItemCount": 2, "unreadItemCount": 1}],
        }
        self.messages = {
            "root": [{"id": "m1", "conversationId": "c1", "subject": "Root", "bodyPreview": "root", "from": {"emailAddress": {"address": "a@example.com"}}, "receivedDateTime": "2026-06-04T00:00:00Z", "isRead": False}],
            "child": [{"id": "m2", "conversationId": "c2", "subject": "Child", "bodyPreview": "child", "from": {"emailAddress": {"address": "b@example.com"}}, "receivedDateTime": "2026-06-04T00:00:00Z", "isRead": True}],
        }

    async def resolve_folder(self, folder: str):
        return self._folder_from_graph({"id": "root", "displayName": "Inbox", "childFolderCount": 1, "totalItemCount": 1, "unreadItemCount": 0}, "Inbox")

    async def list_child_folders(self, folder_id: str, parent_path: str, include_hidden: bool = False):
        return [self._folder_from_graph(raw, f"{parent_path}/{raw['displayName']}") for raw in self.children.get(folder_id, [])]

    async def _get_messages(self, folder_id: str, top: int):
        return self.messages.get(folder_id, [])[:top]


@pytest.mark.asyncio
async def test_recursive_folder_sync_preserves_hierarchical_paths():
    messages = await FakeGraphClient().list_messages_recursive("Inbox", top_per_folder=25)
    assert {message["graph_id"] for message in messages} == {"m1", "m2"}
    assert {message["folder"] for message in messages} == {"Inbox", "Inbox/Important"}
