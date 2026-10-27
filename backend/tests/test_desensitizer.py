"""
Unit tests for backend/app/services/desensitizer.py.

Validates that PII regex patterns and key-info-driven entity replacement work
together to produce a redacted text + a per-type summary.
"""

from __future__ import annotations

from backend.app.services.desensitizer import desensitize_text


def _types(result):
    return {item["type"] for item in result.redaction_summary}


def test_email_redacted():
    result = desensitize_text("Contact alice@example.com for support.")
    assert "[EMAIL]" in result.redacted_text
    assert "alice@example.com" not in result.redacted_text
    assert "EMAIL" in _types(result)
    assert result.total_redactions >= 1


def test_phone_redacted():
    result = desensitize_text("Call +44 7700 900123 anytime.")
    assert "[PHONE]" in result.redacted_text
    assert "PHONE" in _types(result)


def test_ssn_redacted():
    result = desensitize_text("My SSN is 123-45-6789, please keep it safe.")
    assert "[SSN]" in result.redacted_text
    assert "SSN" in _types(result)


def test_passport_redacted():
    result = desensitize_text("Passport No. AB1234567 issued in 2020.")
    assert "[PASSPORT]" in result.redacted_text
    assert "PASSPORT" in _types(result)


def test_date_of_birth_redacted():
    result = desensitize_text("Date of birth: 1990-05-12 (London).")
    assert "[DATE OF BIRTH]" in result.redacted_text
    assert "DATE OF BIRTH" in _types(result)


def test_address_redacted_when_no_work_location_in_key_info():
    result = desensitize_text("Residing at 221B Baker Street London NW1 6XE.")
    assert "[ADDRESS]" in result.redacted_text
    assert "ADDRESS" in _types(result)


def test_address_not_redacted_when_work_location_known():
    """If key_info already records work_location, the ADDRESS regex is skipped."""
    result = desensitize_text(
        "Residing at 221B Baker Street London NW1 6XE.",
        key_info={"work_location": "London Office"},
    )
    assert "[ADDRESS]" not in result.redacted_text
    assert "ADDRESS" not in _types(result)


def test_employer_employee_replaced_from_key_info():
    text = "This Agreement is between Acme Corporation and John Doe."
    result = desensitize_text(
        text,
        key_info={
            "party_a": "Acme Corporation",
            "party_b": "John Doe",
            "salary_amount": "5000 USD",
        },
    )
    assert "[EMPLOYER]" in result.redacted_text
    assert "[EMPLOYEE]" in result.redacted_text
    assert "Acme Corporation" not in result.redacted_text
    assert "John Doe" not in result.redacted_text


def test_salary_amount_replaced():
    result = desensitize_text(
        "The agreed monthly salary is 5000 USD.",
        key_info={"salary_amount": "5000 USD"},
    )
    assert "[SALARY]" in result.redacted_text


def test_not_identified_values_skipped():
    """Placeholder strings 'Not identified' must not be substituted."""
    result = desensitize_text(
        "Acme Corp employs John Doe.",
        key_info={
            "party_a": "Not identified",
            "party_b": "John Doe",
        },
    )
    assert "Acme Corp" in result.redacted_text  # not replaced
    assert "[EMPLOYEE]" in result.redacted_text


def test_summary_sorted_by_count_desc():
    text = (
        "Email1: a@x.com, Email2: b@x.com, Email3: c@x.com. "
        "Call +44 7700 900123 today."
    )
    result = desensitize_text(text)
    # EMAIL count (3) > PHONE count (1) → EMAIL first
    assert result.redaction_summary[0]["type"] == "EMAIL"
    assert int(result.redaction_summary[0]["count"]) == 3


def test_empty_text_returns_empty_summary():
    result = desensitize_text("")
    assert result.redacted_text == ""
    assert result.redaction_summary == []
    assert result.total_redactions == 0


def test_none_key_info_handled_gracefully():
    result = desensitize_text("Email me at x@y.com.", key_info=None)
    assert "[EMAIL]" in result.redacted_text


def test_combined_pii():
    text = (
        "Acme Corp hires John Doe, email john@acme.com, "
        "phone +44 7700 900123, SSN 111-22-3333. "
        "Date of birth: 1990-05-12. Salary 5000 USD."
    )
    result = desensitize_text(
        text,
        key_info={
            "party_a": "Acme Corp",
            "party_b": "John Doe",
            "salary_amount": "5000 USD",
        },
    )
    types = _types(result)
    assert {"EMPLOYER", "EMPLOYEE", "EMAIL", "PHONE", "SSN", "DATE OF BIRTH", "SALARY"} <= types
    assert result.total_redactions >= 7
