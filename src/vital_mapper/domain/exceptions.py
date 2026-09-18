class DomainError(Exception):
    """Basisklasse fuer alle fachlichen Fehler."""


class UngroundedExtractionError(DomainError):
    """Die Extraktion enthaelt einen Wert, der nicht im Transkript nachweisbar
    ist - Verstoss gegen F-08. Wird vom Grounding-Check ausgeloest, siehe
    infrastructure/ollama/ollama_adapter.py."""


class AccessDeniedError(DomainError):
    """Zugriff auf Patientendaten ohne gueltige Rolle oder Vertretungszugriff
    (F-31/F-32)."""


class DraftAlreadyApprovedError(DomainError):
    """Ein bereits freigegebener Entwurf darf nicht erneut veraendert werden
    (UC-06)."""


class DraftNotEditableError(DomainError):
    """Ein verworfener Entwurf darf nicht mehr freigegeben werden (F-24)."""


class DraftNotFoundError(DomainError):
    """Der angeforderte Entwurf existiert nicht."""


class RecordingNotFoundError(DomainError):
    """Die angeforderte Aufnahme existiert nicht."""


class TranscriptNotFoundError(DomainError):
    """Das angeforderte Transkript existiert nicht."""


class ExtractionNotFoundError(DomainError):
    """Die angeforderte Extraktion existiert nicht."""


class InvalidCredentialsError(DomainError):
    """Benutzername oder Passwort sind ungueltig (F-30)."""


class UserAlreadyExistsError(DomainError):
    """Der Benutzername ist bereits vergeben (F-30)."""


class PasswordPolicyError(DomainError):
    """Das Passwort erfuellt die Mindestanforderungen nicht (F-30)."""


class UsernamePolicyError(DomainError):
    """Der Benutzername erfuellt die Mindestanforderungen nicht (F-30)."""
