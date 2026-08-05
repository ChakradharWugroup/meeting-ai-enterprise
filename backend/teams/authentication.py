class TeamsAuthenticator:
    def __init__(self, tenant_id: str, client_id: str):
        self.tenant_id = tenant_id
        self.client_id = client_id

    def validate_token(self, token: str) -> bool:
        """
        Validates an incoming Azure AD Bearer token from a client or webhook.
        """
        print(f"Validating token... {token[:10]}...")
        # Mock validation
        return True
