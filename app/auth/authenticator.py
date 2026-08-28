"""Abstract authenticator interface and mock implementation."""

from __future__ import annotations

from abc import ABC, abstractmethod


class Authenticator(ABC):
    """Abstract base class for authentication backends."""

    @abstractmethod
    def authenticate(self, username: str, password: str) -> bool:
        """Authenticate a user. Must never store credentials."""
        ...

    @abstractmethod
    def get_available_users(self) -> list[str]:
        """Return list of usernames available for login."""
        ...


class MockAuthenticator(Authenticator):
    """Mock authenticator for development mode.

    Accepts username='dev', password='dev'.
    """

    MOCK_USER = "dev"
    MOCK_PASSWORD = "dev"

    def authenticate(self, username: str, password: str) -> bool:
        return username == self.MOCK_USER and password == self.MOCK_PASSWORD

    def get_available_users(self) -> list[str]:
        return [self.MOCK_USER]
