"""Per-process bearer token with constant-time verification."""
from secrets import compare_digest, token_urlsafe

class SessionToken:
    def __init__(self) -> None:
        self._value = token_urlsafe(32)

    @property
    def value(self) -> str:
        return self._value

    def verify(self, candidate: str | None) -> bool:
        return isinstance(candidate, str) and bool(candidate) and compare_digest(self._value, candidate)
