"""
Unit tests for backend/app/services/missing_checker.detect_missing_items.

Pure-keyword presence check — no DB or NLP model required.
"""

from __future__ import annotations

import pytest

from backend.app.services.missing_checker import detect_missing_items


def _names(items):
    return [m["item_name"] for m in items]


def test_labor_contract_missing_all_when_clauses_empty():
    items = detect_missing_items([{"content": ""}], "labor")
    names = _names(items)
    assert "Salary / Remuneration" in names
    assert "Work Location" in names
    assert "Contract Term" in names
    assert "Dispute Resolution" in names
    assert "Termination Conditions" in names
    assert "Working Hours" in names
    assert "Breach Liability" in names


def test_labor_contract_with_salary_keyword_omits_that_item():
    clauses = [{"content": "The monthly salary is 5000 USD payable on the 10th."}]
    items = detect_missing_items(clauses, "labor")
    assert "Salary / Remuneration" not in _names(items)


def test_labor_contract_with_chinese_salary_keyword():
    clauses = [{"content": "每月工资为5000元。"}]
    items = detect_missing_items(clauses, "labor")
    assert "Salary / Remuneration" not in _names(items)


def test_labor_contract_full_coverage_returns_empty():
    clauses = [{
        "content": (
            "salary work location contract term dispute terminate "
            "working hours breach"
        ),
    }]
    items = detect_missing_items(clauses, "labor")
    assert items == []


def test_internship_contract_specific_items():
    items = detect_missing_items([{"content": ""}], "internship")
    names = _names(items)
    assert "Stipend / Allowance" in names
    assert "Internship Duration" in names
    assert "Supervisor / Mentor" in names


def test_service_contract_specific_items():
    items = detect_missing_items([{"content": ""}], "service")
    names = _names(items)
    assert "Service Fee / Remuneration" in names
    assert "Scope of Services" in names


def test_unknown_contract_type_falls_back_to_labor():
    items = detect_missing_items([{"content": ""}], "unknown")
    names = _names(items)
    # "labor" is the default fallback in REQUIRED_BY_TYPE.get
    assert "Salary / Remuneration" in names


@pytest.mark.parametrize("contract_type", ["labor", "internship", "service"])
def test_each_missing_item_has_required_keys(contract_type):
    items = detect_missing_items([{"content": ""}], contract_type)
    for item in items:
        assert {"item_name", "description", "potential_risk"} <= set(item.keys())
        assert item["description"]
        assert item["potential_risk"]
