"""
Minimal API key store. In production this would come from a database,
secrets manager, or env-var-driven config — not a hardcoded dict.
"""

API_KEYS = {
    "sk_live_abc123": "client_alpha",
    "sk_live_xyz789": "client_beta",
}


def resolve_client_id(api_key: str | None) -> str | None:
    """Returns the client_id for a valid key, or None if invalid/missing."""
    if not api_key:
        return None
    return API_KEYS.get(api_key)
