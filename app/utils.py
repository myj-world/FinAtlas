import re
from typing import Optional


def normalize_name(name: Optional[str]) -> str:
    """Normalize a name for deterministic matching."""
    if not name:
        return ""
    lowered = name.lower()
    cleaned = re.sub(r"[^\w\s]", "", lowered)
    collapsed = re.sub(r"\s+", "", cleaned)
    return collapsed.strip()


def extract_bearer_token(headers) -> Optional[str]:
    """Return the Bearer token from an authorization header, if present."""
    auth = headers.get("Authorization") or headers.get("authorization")
    if not auth:
        return None
    parts = auth.split()
    if len(parts) == 2 and parts[0].lower() == "bearer":
        return parts[1]
    return None
