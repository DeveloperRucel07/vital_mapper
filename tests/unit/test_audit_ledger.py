from datetime import UTC, datetime

from vital_mapper.infrastructure.security.audit import (
    AuditEntry,
    calculate_entry_hash,
    is_valid_audit_chain,
)


def test_audit_chain_accepts_intact_entries() -> None:
    occurred_at = datetime(2026, 9, 30, 10, 0, tzinfo=UTC)
    first_hash = calculate_entry_hash(
        occurred_at, "user-1", "patient-1", "read_draft", "read_draft", ""
    )
    second_hash = calculate_entry_hash(
        occurred_at, "user-1", "patient-1", "update_draft", "update_draft", first_hash
    )
    entries = [
        AuditEntry(occurred_at, "user-1", "patient-1", "read_draft", "read_draft", "", first_hash),
        AuditEntry(
            occurred_at,
            "user-1",
            "patient-1",
            "update_draft",
            "update_draft",
            first_hash,
            second_hash,
        ),
    ]

    assert is_valid_audit_chain(entries, second_hash)


def test_audit_chain_detects_changed_action_or_end_anchor() -> None:
    occurred_at = datetime(2026, 9, 30, 10, 0, tzinfo=UTC)
    entry_hash = calculate_entry_hash(
        occurred_at, "user-1", "patient-1", "read_draft", "read_draft", ""
    )
    changed_entry = AuditEntry(
        occurred_at,
        "user-1",
        "patient-1",
        "approve_draft",
        "read_draft",
        "",
        entry_hash,
    )

    assert not is_valid_audit_chain([changed_entry], entry_hash)
    assert not is_valid_audit_chain([], entry_hash)
