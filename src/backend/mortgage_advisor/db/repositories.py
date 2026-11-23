"""Repositories: data access for loan servicing.

`ServicingDatabase` stores loans, payments and payment methods in SQLite.
Data survives server restarts (unlike the in-memory origination store).
The schema comes from `migrations/`; the database is seeded from
`data/mortgage/servicing_seed.json` on first run.
"""
from __future__ import annotations

import json
import logging
import sqlite3
import uuid
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Optional

from mortgage_advisor.db.models import (
    DelinquencyStage,
    DelinquencyStatus,
    ForbearanceRequest,
    LoanAccount,
    LossMitigationStatus,
    PaymentHistory,
    PaymentMethod,
    PaymentMethodType,
    PaymentPlan,
    PaymentSchedule,
    PaymentStatus,
)

log = logging.getLogger("mortgage_advisor.db.repositories")

from mortgage_advisor.core.config import SERVICING_DB_PATH as DB_PATH
from mortgage_advisor.core.config import SERVICING_SEED_PATH as SEED_PATH
from mortgage_advisor.db.session import apply_migrations, connect


def _new_id(prefix: str) -> str:
    """Generate a new ID with prefix."""
    return f"{prefix}{uuid.uuid4().hex[:8].upper()}"


class ServicingDatabase:
    """SQLite adapter for loan servicing data."""

    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        self._init_db()

    def _conn(self):
        """Context manager for database connections."""
        return connect(self.db_path)

    def _init_db(self) -> None:
        """Apply the schema migrations if needed."""
        with self._conn() as conn:
            apply_migrations(conn)

        # Seed data if database is empty
        if self._is_empty():
            self._seed_data()

    def _is_empty(self) -> bool:
        """Check if the database has any loans."""
        with self._conn() as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM loans")
            return cursor.fetchone()[0] == 0

    def _seed_data(self) -> None:
        """Load seed data from JSON file."""
        if not SEED_PATH.exists():
            log.warning("Seed file not found: %s", SEED_PATH)
            return

        log.info("Seeding servicing database from %s", SEED_PATH)
        seed = json.loads(SEED_PATH.read_text(encoding="utf-8"))

        with self._conn() as conn:
            # Load loans
            for loan_data in seed.get("loans", []):
                self._insert_loan(conn, loan_data)

            # Load payment methods
            for method_data in seed.get("payment_methods", []):
                self._insert_payment_method(conn, method_data)

            # Load payment history
            for payment_data in seed.get("payment_history", []):
                self._insert_payment_history(conn, payment_data)

            # Load payment schedules
            for schedule_data in seed.get("payment_schedules", []):
                self._insert_payment_schedule(conn, schedule_data)

    def _insert_loan(self, conn: sqlite3.Connection, data: dict) -> None:
        """Insert a loan record."""
        conn.execute("""
            INSERT OR REPLACE INTO loans (
                id, customer_id, customer_name, property_address,
                original_amount, current_balance, interest_rate, monthly_payment,
                loan_type, term_months, remaining_months, payment_day,
                next_due_date, escrow_balance, autopay_enabled, autopay_payment_method_id,
                origination_date, maturity_date, last_payment_date, is_active
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            data["id"], data["customer_id"], data["customer_name"], data["property_address"],
            data["original_amount"], data["current_balance"], data["interest_rate"],
            data["monthly_payment"], data["loan_type"], data["term_months"],
            data["remaining_months"], data["payment_day"], data["next_due_date"],
            data["escrow_balance"], data.get("autopay_enabled", False),
            data.get("autopay_payment_method_id"),
            data["origination_date"], data.get("maturity_date"),
            data.get("last_payment_date"), data.get("is_active", True)
        ))

    def _insert_payment_method(self, conn: sqlite3.Connection, data: dict) -> None:
        """Insert a payment method record."""
        conn.execute("""
            INSERT OR REPLACE INTO payment_methods (
                id, customer_id, method_type, last_four, institution_name,
                nickname, is_default, is_autopay, token, expiration_date, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            data["id"], data["customer_id"], data["method_type"], data["last_four"],
            data["institution_name"], data.get("nickname"), data.get("is_default", False),
            data.get("is_autopay", False), data.get("token", ""),
            data.get("expiration_date"), data.get("created_at", datetime.now().isoformat())
        ))

    def _insert_payment_history(self, conn: sqlite3.Connection, data: dict) -> None:
        """Insert a payment history record."""
        conn.execute("""
            INSERT OR REPLACE INTO payment_history (
                id, loan_id, payment_date, amount, principal_applied,
                interest_applied, escrow_applied, payment_method_id,
                payment_method_last_four, status, confirmation_number,
                posted_date, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            data["id"], data["loan_id"], data["payment_date"], data["amount"],
            data["principal_applied"], data["interest_applied"], data["escrow_applied"],
            data["payment_method_id"], data["payment_method_last_four"],
            data["status"], data["confirmation_number"],
            data.get("posted_date"), data.get("created_at", datetime.now().isoformat())
        ))

    def _insert_payment_schedule(self, conn: sqlite3.Connection, data: dict) -> None:
        """Insert a payment schedule record."""
        conn.execute("""
            INSERT OR REPLACE INTO payment_schedules (
                id, loan_id, due_date, principal_amount, interest_amount,
                escrow_amount, total_amount, status, paid_date, paid_amount,
                payment_method_id, confirmation_number
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            data["id"], data["loan_id"], data["due_date"], data["principal_amount"],
            data["interest_amount"], data["escrow_amount"], data["total_amount"],
            data.get("status", "scheduled"), data.get("paid_date"),
            data.get("paid_amount"), data.get("payment_method_id"),
            data.get("confirmation_number")
        ))

    # --------------------------------------------------------------------- Loans
    def get_loan(self, loan_id: str) -> Optional[LoanAccount]:
        """Get a loan by ID."""
        with self._conn() as conn:
            cursor = conn.execute("SELECT * FROM loans WHERE id = ?", (loan_id,))
            row = cursor.fetchone()
            return self._row_to_loan(row) if row else None

    def get_loan_by_customer(self, customer_id: str) -> Optional[LoanAccount]:
        """Get the primary loan for a customer."""
        with self._conn() as conn:
            cursor = conn.execute(
                "SELECT * FROM loans WHERE customer_id = ? AND is_active = 1 LIMIT 1",
                (customer_id,)
            )
            row = cursor.fetchone()
            return self._row_to_loan(row) if row else None

    def get_loans_by_customer(self, customer_id: str) -> list[LoanAccount]:
        """Get all active loans for a customer."""
        with self._conn() as conn:
            cursor = conn.execute(
                "SELECT * FROM loans WHERE customer_id = ? AND is_active = 1",
                (customer_id,)
            )
            return [self._row_to_loan(row) for row in cursor.fetchall()]

    def update_loan(self, loan: LoanAccount) -> None:
        """Update a loan record."""
        with self._conn() as conn:
            conn.execute("""
                UPDATE loans SET
                    current_balance = ?, monthly_payment = ?, remaining_months = ?,
                    payment_day = ?, next_due_date = ?, escrow_balance = ?,
                    autopay_enabled = ?, autopay_payment_method_id = ?,
                    last_payment_date = ?, is_active = ?
                WHERE id = ?
            """, (
                str(loan.current_balance), str(loan.monthly_payment), loan.remaining_months,
                loan.payment_day, loan.next_due_date.isoformat(), str(loan.escrow_balance),
                loan.autopay_enabled, loan.autopay_payment_method_id,
                loan.last_payment_date.isoformat() if loan.last_payment_date else None,
                loan.is_active, loan.id
            ))

    def _row_to_loan(self, row: sqlite3.Row) -> LoanAccount:
        """Convert a database row to a LoanAccount."""
        return LoanAccount(
            id=row["id"],
            customer_id=row["customer_id"],
            customer_name=row["customer_name"],
            property_address=row["property_address"],
            original_amount=Decimal(str(row["original_amount"])),
            current_balance=Decimal(str(row["current_balance"])),
            interest_rate=Decimal(str(row["interest_rate"])),
            monthly_payment=Decimal(str(row["monthly_payment"])),
            loan_type=row["loan_type"],
            term_months=row["term_months"],
            remaining_months=row["remaining_months"],
            payment_day=row["payment_day"],
            next_due_date=date.fromisoformat(row["next_due_date"]),
            escrow_balance=Decimal(str(row["escrow_balance"])),
            autopay_enabled=bool(row["autopay_enabled"]),
            autopay_payment_method_id=row["autopay_payment_method_id"],
            origination_date=date.fromisoformat(row["origination_date"]),
            maturity_date=date.fromisoformat(row["maturity_date"]) if row["maturity_date"] else None,
            last_payment_date=date.fromisoformat(row["last_payment_date"]) if row["last_payment_date"] else None,
            is_active=bool(row["is_active"])
        )

    # --------------------------------------------------------------------- Payment Methods
    def get_payment_method(self, method_id: str) -> Optional[PaymentMethod]:
        """Get a payment method by ID."""
        with self._conn() as conn:
            cursor = conn.execute("SELECT * FROM payment_methods WHERE id = ?", (method_id,))
            row = cursor.fetchone()
            return self._row_to_payment_method(row) if row else None

    def get_payment_methods_by_customer(self, customer_id: str) -> list[PaymentMethod]:
        """Get all payment methods for a customer."""
        with self._conn() as conn:
            cursor = conn.execute(
                "SELECT * FROM payment_methods WHERE customer_id = ? ORDER BY is_default DESC, created_at DESC",
                (customer_id,)
            )
            return [self._row_to_payment_method(row) for row in cursor.fetchall()]

    def get_default_payment_method(self, customer_id: str) -> Optional[PaymentMethod]:
        """Get the default payment method for a customer."""
        with self._conn() as conn:
            cursor = conn.execute(
                "SELECT * FROM payment_methods WHERE customer_id = ? AND is_default = 1 LIMIT 1",
                (customer_id,)
            )
            row = cursor.fetchone()
            return self._row_to_payment_method(row) if row else None

    def add_payment_method(self, method: PaymentMethod) -> PaymentMethod:
        """Add a new payment method."""
        method.id = method.id or _new_id("PM")
        with self._conn() as conn:
            conn.execute("""
                INSERT INTO payment_methods (
                    id, customer_id, method_type, last_four, institution_name,
                    nickname, is_default, is_autopay, token, expiration_date, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                method.id, method.customer_id, method.method_type.value, method.last_four,
                method.institution_name, method.nickname, method.is_default,
                method.is_autopay, method.token, method.expiration_date,
                method.created_at.isoformat()
            ))
        return method

    def update_payment_method(self, method: PaymentMethod) -> None:
        """Update a payment method."""
        with self._conn() as conn:
            conn.execute("""
                UPDATE payment_methods SET
                    nickname = ?, is_default = ?, is_autopay = ?, token = ?, expiration_date = ?
                WHERE id = ?
            """, (
                method.nickname, method.is_default, method.is_autopay,
                method.token, method.expiration_date, method.id
            ))

    def set_default_payment_method(self, customer_id: str, method_id: str) -> None:
        """Set a payment method as the default, clearing others."""
        with self._conn() as conn:
            conn.execute(
                "UPDATE payment_methods SET is_default = 0 WHERE customer_id = ?",
                (customer_id,)
            )
            conn.execute(
                "UPDATE payment_methods SET is_default = 1 WHERE id = ?",
                (method_id,)
            )

    def delete_payment_method(self, method_id: str) -> bool:
        """Delete a payment method. Returns True if deleted."""
        with self._conn() as conn:
            cursor = conn.execute("DELETE FROM payment_methods WHERE id = ?", (method_id,))
            return cursor.rowcount > 0

    def _row_to_payment_method(self, row: sqlite3.Row) -> PaymentMethod:
        """Convert a database row to a PaymentMethod."""
        return PaymentMethod(
            id=row["id"],
            customer_id=row["customer_id"],
            method_type=PaymentMethodType(row["method_type"]),
            last_four=row["last_four"],
            institution_name=row["institution_name"],
            nickname=row["nickname"],
            is_default=bool(row["is_default"]),
            is_autopay=bool(row["is_autopay"]),
            token=row["token"] or "",
            expiration_date=row["expiration_date"],
            created_at=datetime.fromisoformat(row["created_at"]) if row["created_at"] else datetime.now()
        )

    # --------------------------------------------------------------------- Payment History
    def get_payment_history(self, loan_id: str, limit: int = 12) -> list[PaymentHistory]:
        """Get recent payment history for a loan."""
        with self._conn() as conn:
            cursor = conn.execute(
                "SELECT * FROM payment_history WHERE loan_id = ? ORDER BY payment_date DESC LIMIT ?",
                (loan_id, limit)
            )
            return [self._row_to_payment_history(row) for row in cursor.fetchall()]

    def add_payment(self, payment: PaymentHistory) -> PaymentHistory:
        """Record a new payment."""
        payment.id = payment.id or _new_id("PAY")
        payment.confirmation_number = payment.confirmation_number or _new_id("REF")
        with self._conn() as conn:
            conn.execute("""
                INSERT INTO payment_history (
                    id, loan_id, payment_date, amount, principal_applied,
                    interest_applied, escrow_applied, payment_method_id,
                    payment_method_last_four, status, confirmation_number,
                    posted_date, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                payment.id, payment.loan_id, payment.payment_date.isoformat(),
                str(payment.amount), str(payment.principal_applied),
                str(payment.interest_applied), str(payment.escrow_applied),
                payment.payment_method_id, payment.payment_method_last_four,
                payment.status.value, payment.confirmation_number,
                payment.posted_date.isoformat() if payment.posted_date else None,
                payment.created_at.isoformat()
            ))
        return payment

    def _row_to_payment_history(self, row: sqlite3.Row) -> PaymentHistory:
        """Convert a database row to a PaymentHistory."""
        return PaymentHistory(
            id=row["id"],
            loan_id=row["loan_id"],
            payment_date=date.fromisoformat(row["payment_date"]),
            amount=Decimal(str(row["amount"])),
            principal_applied=Decimal(str(row["principal_applied"])),
            interest_applied=Decimal(str(row["interest_applied"])),
            escrow_applied=Decimal(str(row["escrow_applied"])),
            payment_method_id=row["payment_method_id"],
            payment_method_last_four=row["payment_method_last_four"],
            status=PaymentStatus(row["status"]),
            confirmation_number=row["confirmation_number"],
            posted_date=date.fromisoformat(row["posted_date"]) if row["posted_date"] else None,
            created_at=datetime.fromisoformat(row["created_at"]) if row["created_at"] else datetime.now()
        )

    # --------------------------------------------------------------------- Payment Schedule
    def get_payment_schedule(self, loan_id: str, limit: int = 12) -> list[PaymentSchedule]:
        """Get upcoming payment schedule for a loan."""
        with self._conn() as conn:
            cursor = conn.execute(
                """SELECT * FROM payment_schedules
                   WHERE loan_id = ? AND status != 'completed'
                   ORDER BY due_date ASC LIMIT ?""",
                (loan_id, limit)
            )
            return [self._row_to_payment_schedule(row) for row in cursor.fetchall()]

    def get_next_payment(self, loan_id: str) -> Optional[PaymentSchedule]:
        """Get the next scheduled payment for a loan."""
        with self._conn() as conn:
            cursor = conn.execute(
                """SELECT * FROM payment_schedules
                   WHERE loan_id = ? AND status IN ('scheduled', 'pending')
                   ORDER BY due_date ASC LIMIT 1""",
                (loan_id,)
            )
            row = cursor.fetchone()
            return self._row_to_payment_schedule(row) if row else None

    def get_past_due_payments(self, loan_id: str) -> list[PaymentSchedule]:
        """Get all past due payments for a loan."""
        today = date.today().isoformat()
        with self._conn() as conn:
            cursor = conn.execute(
                """SELECT * FROM payment_schedules
                   WHERE loan_id = ? AND status NOT IN ('completed')
                   AND due_date < ?
                   ORDER BY due_date ASC""",
                (loan_id, today)
            )
            return [self._row_to_payment_schedule(row) for row in cursor.fetchall()]

    def update_payment_schedule(self, schedule: PaymentSchedule) -> None:
        """Update a payment schedule record."""
        with self._conn() as conn:
            conn.execute("""
                UPDATE payment_schedules SET
                    status = ?, paid_date = ?, paid_amount = ?,
                    payment_method_id = ?, confirmation_number = ?
                WHERE id = ?
            """, (
                schedule.status.value,
                schedule.paid_date.isoformat() if schedule.paid_date else None,
                str(schedule.paid_amount) if schedule.paid_amount else None,
                schedule.payment_method_id, schedule.confirmation_number,
                schedule.id
            ))

    def _row_to_payment_schedule(self, row: sqlite3.Row) -> PaymentSchedule:
        """Convert a database row to a PaymentSchedule."""
        return PaymentSchedule(
            id=row["id"],
            loan_id=row["loan_id"],
            due_date=date.fromisoformat(row["due_date"]),
            principal_amount=Decimal(str(row["principal_amount"])),
            interest_amount=Decimal(str(row["interest_amount"])),
            escrow_amount=Decimal(str(row["escrow_amount"])),
            total_amount=Decimal(str(row["total_amount"])),
            status=PaymentStatus(row["status"]),
            paid_date=date.fromisoformat(row["paid_date"]) if row["paid_date"] else None,
            paid_amount=Decimal(str(row["paid_amount"])) if row["paid_amount"] else None,
            payment_method_id=row["payment_method_id"],
            confirmation_number=row["confirmation_number"]
        )

    # --------------------------------------------------------------------- Delinquency
    def get_delinquency_status(self, loan_id: str) -> DelinquencyStatus:
        """Calculate delinquency status for a loan."""
        past_due = self.get_past_due_payments(loan_id)
        if not past_due:
            return DelinquencyStatus(loan_id=loan_id)

        # Calculate days past due from oldest unpaid payment
        oldest = min(p.due_date for p in past_due)
        dpd = (date.today() - oldest).days
        amount_past_due = sum(p.total_amount for p in past_due)

        return DelinquencyStatus.from_days(loan_id, dpd, amount_past_due)

    # --------------------------------------------------------------------- Collections Tools
    def add_forbearance_request(self, request: ForbearanceRequest) -> ForbearanceRequest:
        """Create a forbearance request."""
        request.id = request.id or _new_id("FB")
        with self._conn() as conn:
            conn.execute("""
                INSERT INTO forbearance_requests (
                    id, loan_id, customer_id, request_date, reason, requested_months,
                    status, approved_months, start_date, end_date, notes, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                request.id, request.loan_id, request.customer_id,
                request.request_date.isoformat(), request.reason, request.requested_months,
                request.status.value, request.approved_months,
                request.start_date.isoformat() if request.start_date else None,
                request.end_date.isoformat() if request.end_date else None,
                request.notes, request.created_at.isoformat()
            ))
        return request

    def get_forbearance_request(self, loan_id: str) -> Optional[ForbearanceRequest]:
        """Get the most recent forbearance request for a loan."""
        with self._conn() as conn:
            cursor = conn.execute(
                """SELECT * FROM forbearance_requests
                   WHERE loan_id = ?
                   ORDER BY created_at DESC LIMIT 1""",
                (loan_id,)
            )
            row = cursor.fetchone()
            if not row:
                return None
            return ForbearanceRequest(
                id=row["id"],
                loan_id=row["loan_id"],
                customer_id=row["customer_id"],
                request_date=date.fromisoformat(row["request_date"]),
                reason=row["reason"],
                requested_months=row["requested_months"],
                status=LossMitigationStatus(row["status"]),
                approved_months=row["approved_months"],
                start_date=date.fromisoformat(row["start_date"]) if row["start_date"] else None,
                end_date=date.fromisoformat(row["end_date"]) if row["end_date"] else None,
                notes=row["notes"] or "",
                created_at=datetime.fromisoformat(row["created_at"])
            )

    def add_payment_plan(self, plan: PaymentPlan) -> PaymentPlan:
        """Create a payment plan for past-due amounts."""
        plan.id = plan.id or _new_id("PP")
        with self._conn() as conn:
            conn.execute("""
                INSERT INTO payment_plans (
                    id, loan_id, start_date, end_date, total_past_due,
                    additional_monthly_amount, payments_remaining, status, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                plan.id, plan.loan_id, plan.start_date.isoformat(),
                plan.end_date.isoformat(), str(plan.total_past_due),
                str(plan.additional_monthly_amount), plan.payments_remaining,
                plan.status, plan.created_at.isoformat()
            ))
        return plan

    def get_payment_plan(self, loan_id: str) -> Optional[PaymentPlan]:
        """Get the active payment plan for a loan."""
        with self._conn() as conn:
            cursor = conn.execute(
                """SELECT * FROM payment_plans
                   WHERE loan_id = ? AND status = 'active'
                   ORDER BY created_at DESC LIMIT 1""",
                (loan_id,)
            )
            row = cursor.fetchone()
            if not row:
                return None
            return PaymentPlan(
                id=row["id"],
                loan_id=row["loan_id"],
                start_date=date.fromisoformat(row["start_date"]),
                end_date=date.fromisoformat(row["end_date"]),
                total_past_due=Decimal(str(row["total_past_due"])),
                additional_monthly_amount=Decimal(str(row["additional_monthly_amount"])),
                payments_remaining=row["payments_remaining"],
                status=row["status"],
                created_at=datetime.fromisoformat(row["created_at"])
            )

    # --------------------------------------------------------------------- Utilities
    def reset_database(self) -> None:
        """Reset the database to seed data (for testing)."""
        with self._conn() as conn:
            conn.executescript("""
                DELETE FROM payment_plans;
                DELETE FROM forbearance_requests;
                DELETE FROM payment_history;
                DELETE FROM payment_schedules;
                DELETE FROM payment_methods;
                DELETE FROM loans;
            """)
        self._seed_data()


# Singleton instance
_db: Optional[ServicingDatabase] = None


def get_servicing_db() -> ServicingDatabase:
    """Get or create the singleton database instance."""
    global _db
    if _db is None:
        _db = ServicingDatabase()
    return _db


def use_servicing_db(db: ServicingDatabase) -> None:
    """Swap the database instance (for testing)."""
    global _db
    _db = db
