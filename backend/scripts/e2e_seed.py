#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from flask import current_app

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
from backend.app import create_app
from backend.app.extensions import db
from backend.app.models.clause import Clause
from backend.app.models.contract import Contract
from backend.app.models.missing import MissingItem
from backend.app.models.risk import RiskItem
from backend.app.models.user import User
from backend.app.services.auth_service import hash_password
from backend.app.services.share_service import create_share_link


def reset_db() -> None:
    db.session.remove()
    db.drop_all()
    db.create_all()


def ensure_user(name: str, email: str, password: str) -> User:
    user = User.query.filter_by(email=email.lower()).first()
    if user:
        user.name = name
        user.password_hash = hash_password(password)
        user.is_active = True
        user.deactivated_at = None
        db.session.commit()
        return user
    user = User(name=name, email=email.lower(), password_hash=hash_password(password), is_active=True)
    db.session.add(user)
    db.session.commit()
    return user


def seed_done_contract(user_id: int, title: str = "e2e_labor_contract.pdf") -> Contract:
    contract = Contract(
        user_id=user_id,
        session_token=None,
        title=title,
        contract_type="labor",
        raw_text=(
            "Article 1 Term: This employment contract is valid for 24 months.\n"
            "Article 2 Salary: Monthly salary is 5000 USD, to be adjusted by the employer.\n"
            "Article 3 Termination: Employer may terminate without prior notice.\n"
            "Article 4 Contact: employee email alice.e2e@example.com, phone +353-123-4567."
        ),
        desensitized_text=(
            "Article 1 Term: This employment contract is valid for 24 months.\n"
            "Article 2 Salary: Monthly salary is [SALARY], to be adjusted by the employer.\n"
            "Article 3 Termination: [EMPLOYER] may terminate without prior notice.\n"
            "Article 4 Contact: employee email [EMAIL], phone [PHONE]."
        ),
        redaction_summary=[
            {"type": "SALARY", "count": 1},
            {"type": "EMPLOYER", "count": 1},
            {"type": "EMAIL", "count": 1},
            {"type": "PHONE", "count": 1},
        ],
        total_redactions=4,
        key_info={
            "contract_name": "Employment Contract",
            "party_a": "ACME Ltd",
            "party_b": "Alice E2E",
            "salary_amount": "5000 USD",
            "work_location": "Dublin",
            "contract_term": "24 months",
            "termination_conditions": "Employer may terminate without notice",
        },
        status="done",
        file_hash=None,
        file_size=1024,
    )
    db.session.add(contract)
    db.session.flush()

    c1 = Clause(
        contract_id=contract.id,
        index_num=1,
        heading="Article 1 Term",
        content="This employment contract is valid for 24 months.",
        category="general",
    )
    c2 = Clause(
        contract_id=contract.id,
        index_num=2,
        heading="Article 2 Salary",
        content="Monthly salary is 5000 USD, to be adjusted by the employer.",
        category="salary",
    )
    c3 = Clause(
        contract_id=contract.id,
        index_num=3,
        heading="Article 3 Termination",
        content="Employer may terminate without prior notice.",
        category="termination",
    )
    db.session.add_all([c1, c2, c3])
    db.session.flush()

    db.session.add_all(
        [
            RiskItem(
                contract_id=contract.id,
                clause_id=c2.id,
                risk_level="medium",
                risk_type="wage_payment_unclear",
                evidence_sentence="Monthly salary is 5000 USD, to be adjusted by the employer.",
                explanation="Salary adjustment rule is vague and may be abused.",
                llm_explanation=None,
                llm_status="skipped",
                legal_reference="For reference only.",
            ),
            RiskItem(
                contract_id=contract.id,
                clause_id=c3.id,
                risk_level="high",
                risk_type="vague_termination",
                evidence_sentence="Employer may terminate without prior notice.",
                explanation="Unilateral termination without notice creates high legal risk.",
                llm_explanation=None,
                llm_status="skipped",
                legal_reference="For reference only.",
            ),
        ]
    )
    db.session.add(
        MissingItem(
            contract_id=contract.id,
            item_name="Dispute Resolution",
            description="No dispute resolution clause detected.",
            potential_risk="Disputes may become costly and hard to enforce.",
        )
    )
    db.session.commit()
    return contract


def bootstrap(payload_path: Path) -> None:
    from backend.app.services.admin_service import ensure_admin_user
    from backend.app.services.template_library_service import ensure_template_library_seeded

    reset_db()
    ensure_admin_user()
    ensure_template_library_seeded()

    user = ensure_user("E2E User", "e2e.user@test.local", "Strong#1234")
    contract = seed_done_contract(user.id)
    share = create_share_link(
        contract_id=contract.id,
        password="Share#1234",
        expires_hours=72,
        max_access_count=50,
    )

    payload = {
        "user": {"email": user.email, "password": "Strong#1234"},
        "admin": {
            "email": current_app.config["ADMIN_EMAIL"],
            "password": current_app.config["ADMIN_PASSWORD"],
        },
        "contract": {"id": contract.id},
        "share": {"token": share.token, "password": "Share#1234"},
    }
    payload_path.parent.mkdir(parents=True, exist_ok=True)
    payload_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(str(payload_path))


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed deterministic backend fixtures for Playwright E2E.")
    parser.add_argument(
        "--output",
        required=True,
        help="Path to write seed metadata JSON.",
    )
    args = parser.parse_args()

    app = create_app()
    with app.app_context():
        bootstrap(Path(args.output))


if __name__ == "__main__":
    main()
