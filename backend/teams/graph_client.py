class GraphClient:
    def __init__(self, tenant_id: str, client_id: str, client_secret: str):
        self.tenant_id = tenant_id
        self.client_id = client_id
        self.client_secret = client_secret

    async def get_access_token(self) -> str:
        # Mock token retrieval
        return "mock_graph_access_token"

    async def get_meeting_participants(self, meeting_id: str) -> list[dict]:
        """
        Fetches the participant roster for a meeting.
        """
        return [{"id": "user1", "name": "Alice"}, {"id": "user2", "name": "Bob"}]
