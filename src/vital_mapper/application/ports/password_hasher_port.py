from abc import ABC, abstractmethod


class PasswordHasherPort(ABC):
    """Port fuer Passwort-Hashing, damit die Anwendung keinen Hashing-Adapter kennt."""

    @abstractmethod
    def hash_password(self, password: str) -> str: ...

    @abstractmethod
    def verify_password(self, password: str, encoded_hash: str) -> bool: ...
