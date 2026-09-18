import os

from cryptography.fernet import Fernet

os.environ.setdefault("AUDIO_ENCRYPTION_KEY", Fernet.generate_key().decode())

import pytest


@pytest.fixture
def sample_transcript() -> str:
    return "Blutdruck 135 zu 80, Puls 76, Schmerzen im rechten Knie vier von zehn."
