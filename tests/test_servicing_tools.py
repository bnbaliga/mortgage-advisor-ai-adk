"""Tests for servicing tool functions and database operations."""

import asyncio
import tempfile
from datetime import date
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

import pytest

from mortgage import servicing_tools, tools
from mortgage.database import ServicingDatabase, use_servicing_db
from mortgage.mortgage import IdentityStrength, MortgageStore
from mortgage.servicing import (
    DelinquencyStage,
    DelinquencyStatus,
    LoanAccount,
    PaymentMethod,
    PaymentMethodType,
)


def run(coro):
    return asyncio.run(coro)


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_servicing.db"
        db = ServicingDatabase(db_path)
        use_servicing_db(db)
        yield db


@pytest.fixture
def store():
    """Create a test store."""
    s = MortgageStore.load()
    tools.use_store(s)
    return s


@pytest.fixture
def ctx(store):
    """Create a mock tool context."""
    ctx = SimpleNamespace(session=SimpleNamespace(id="test-call-1"))
    # Initialize call state
    store.call(ctx.session.id)
    return ctx


@pytest.fixture
def verified_ctx(store, ctx, temp_db):
    """Create a verified context with a customer."""
    call = store.call(ctx.session.id)
    call.verified_customer_id = "C1001"
    call.identity_strength = IdentityStrength.BASIC
    return ctx


@pytest.fixture
def strongly_verified_ctx(store, ctx, temp_db):
    """Create a strongly verified context."""
    call = store.call(ctx.session.id)
    call.verified_customer_id = "C1001"
    call.identity_strength = IdentityStrength.STRONG
    call.verified_loan_id = "LN001"
    return ctx


# --- Database Tests ---


class TestServicingDatabase:
    """Tests for the ServicingDatabase class."""

    def test_database_creates_tables(self, temp_db):
        """Database creates all required tables."""
        # Check that we can query the loans table
        with temp_db._conn() as conn:
            cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = {row[0] for row in cursor.fetchall()}

        assert "loans" in tables
        assert "payment_methods" in tables
        assert "payment_history" in tables
        assert "payment_schedules" in tables
        assert "forbearance_requests" in tables
        assert "payment_plans" in tables

    def test_database_loads_seed_data(self, temp_db):
        """Database loads seed data on first run."""
        loans = temp_db.get_loans_by_customer("C1001")
        # Should have at least one loan from seed data
        assert len(loans) >= 1

    def test_get_loan_by_customer(self, temp_db):
        """Can retrieve a loan by customer ID."""
        loan = temp_db.get_loan_by_customer("C1001")
        assert loan is not None
        assert loan.customer_id == "C1001"
        assert loan.customer_name == "David Martinez"

    def test_get_payment_methods(self, temp_db):
        """Can retrieve payment methods for a customer."""
        methods = temp_db.get_payment_methods_by_customer("C1001")
        assert len(methods) >= 1
        # Check that default is first
        if methods:
            assert methods[0].is_default or len(methods) == 1

    def test_get_payment_history(self, temp_db):
        """Can retrieve payment history for a loan."""
        history = temp_db.get_payment_history("LN001", limit=6)
        assert len(history) >= 1
        # Should be sorted by date descending
        if len(history) > 1:
            assert history[0].payment_date >= history[1].payment_date

    def test_add_payment_method(self, temp_db):
        """Can add a new payment method."""
        method = PaymentMethod(
            id="",
            customer_id="C1001",
            method_type=PaymentMethodType.DEBIT_CARD,
            last_four="9999",
            institution_name="Test Bank",
            nickname="Test Card",
            is_default=False,
            token="tok_test_9999",
        )
        result = temp_db.add_payment_method(method)
        assert result.id.startswith("PM")
        assert result.last_four == "9999"

        # Verify it was saved
        retrieved = temp_db.get_payment_method(result.id)
        assert retrieved is not None
        assert retrieved.last_four == "9999"


# --- Servicing Tools Tests ---


class TestGetLoanBalance:
    """Tests for get_loan_balance tool."""

    def test_requires_verification(self, ctx, temp_db):
        """get_loan_balance requires customer verification."""
        result = run(servicing_tools.get_loan_balance(ctx))
        assert result["result"] == "error"
        assert result["code"] == "not_verified"

    def test_returns_balance_when_verified(self, verified_ctx, temp_db, store):
        """get_loan_balance returns balance for verified customer."""
        result = run(servicing_tools.get_loan_balance(verified_ctx))
        assert result["result"] == "ok"
        assert "current_balance" in result
        assert "monthly_payment" in result
        assert "next_due_date" in result or "next_payment_amount" in result

    def test_stores_verified_loan_id(self, verified_ctx, temp_db, store):
        """get_loan_balance stores the verified loan ID."""
        run(servicing_tools.get_loan_balance(verified_ctx))
        call = store.call(verified_ctx.session.id)
        assert call.verified_loan_id is not None


class TestGetPaymentHistory:
    """Tests for get_payment_history tool."""

    def test_requires_verification(self, ctx, temp_db):
        """get_payment_history requires verification."""
        result = run(servicing_tools.get_payment_history(tool_context=ctx))
        assert result["result"] == "error"
        assert result["code"] == "not_verified"

    def test_returns_payment_list(self, verified_ctx, temp_db):
        """get_payment_history returns list of payments."""
        result = run(servicing_tools.get_payment_history(limit=6, tool_context=verified_ctx))
        assert result["result"] == "ok"
        assert "payments" in result
        assert isinstance(result["payments"], list)

    def test_respects_limit(self, verified_ctx, temp_db):
        """get_payment_history respects the limit parameter."""
        result = run(servicing_tools.get_payment_history(limit=2, tool_context=verified_ctx))
        assert result["result"] == "ok"
        assert len(result["payments"]) <= 2


class TestAutopay:
    """Tests for autopay tools."""

    def test_get_autopay_status(self, verified_ctx, temp_db):
        """get_autopay_status returns current autopay state."""
        result = run(servicing_tools.get_autopay_status(verified_ctx))
        assert result["result"] == "ok"
        assert "autopay_enabled" in result

    def test_setup_autopay_requires_strong_verification(self, verified_ctx, temp_db):
        """setup_autopay requires strong verification."""
        result = run(servicing_tools.setup_autopay(tool_context=verified_ctx))
        assert result["result"] == "error"
        assert result["code"] == "need_strong_verification"

    def test_cancel_autopay_requires_strong_verification(self, verified_ctx, temp_db):
        """cancel_autopay requires strong verification."""
        result = run(servicing_tools.cancel_autopay(verified_ctx))
        assert result["result"] == "error"
        assert result["code"] == "need_strong_verification"


class TestPaymentDateChange:
    """Tests for change_payment_date tool."""

    def test_requires_strong_verification(self, verified_ctx, temp_db):
        """change_payment_date requires strong verification."""
        result = run(servicing_tools.change_payment_date(15, verified_ctx))
        assert result["result"] == "error"
        assert result["code"] == "need_strong_verification"

    def test_validates_day_range(self, strongly_verified_ctx, temp_db):
        """change_payment_date validates day is 1-28."""
        result = run(servicing_tools.change_payment_date(30, strongly_verified_ctx))
        assert result["result"] == "error"
        assert result["code"] == "invalid_day"

        result = run(servicing_tools.change_payment_date(0, strongly_verified_ctx))
        assert result["result"] == "error"
        assert result["code"] == "invalid_day"

    def test_changes_payment_day(self, strongly_verified_ctx, temp_db):
        """change_payment_date updates the payment day."""
        result = run(servicing_tools.change_payment_date(15, strongly_verified_ctx))
        assert result["result"] == "ok"
        assert result["new_day"] == 15
        assert "next_due_date" in result


class TestPaymentMethods:
    """Tests for payment method tools."""

    def test_get_payment_methods_requires_verification(self, ctx, temp_db):
        """get_payment_methods requires verification."""
        result = run(servicing_tools.get_payment_methods(ctx))
        assert result["result"] == "error"

    def test_get_payment_methods_returns_list(self, verified_ctx, temp_db):
        """get_payment_methods returns list of methods."""
        result = run(servicing_tools.get_payment_methods(verified_ctx))
        assert result["result"] == "ok"
        assert "methods" in result


class TestMakePayment:
    """Tests for payment processing tools."""

    def test_prepare_payment_requires_strong_verification(self, verified_ctx, temp_db):
        """prepare_payment requires strong verification."""
        result = run(servicing_tools.prepare_payment(amount=923.33, tool_context=verified_ctx))
        assert result["result"] == "error"
        assert result["code"] == "need_strong_verification"

    def test_prepare_payment_sets_pending_authorization(
        self, strongly_verified_ctx, temp_db, store
    ):
        """prepare_payment sets up pending authorization."""
        result = run(
            servicing_tools.prepare_payment(amount=923.33, tool_context=strongly_verified_ctx)
        )
        assert result["result"] == "ok"
        assert result["status"] == "pending_authorization"

        call = store.call(strongly_verified_ctx.session.id)
        assert call.pending_authorization is not None
        assert call.pending_authorization["amount"] == 923.33

    def test_confirm_payment_requires_pending(self, strongly_verified_ctx, temp_db, store):
        """confirm_payment requires a pending payment."""
        # No pending payment
        result = run(
            servicing_tools.confirm_payment(authorized=True, tool_context=strongly_verified_ctx)
        )
        assert result["result"] == "error"
        assert result["code"] == "no_payment_pending"

    def test_confirm_payment_processes_with_authorization(
        self, strongly_verified_ctx, temp_db, store
    ):
        """confirm_payment processes when authorized."""
        # First prepare a payment
        run(servicing_tools.prepare_payment(amount=923.33, tool_context=strongly_verified_ctx))

        # Then confirm it
        result = run(
            servicing_tools.confirm_payment(authorized=True, tool_context=strongly_verified_ctx)
        )
        assert result["result"] == "ok"
        assert "confirmation_number" in result

        # Authorization should be cleared
        call = store.call(strongly_verified_ctx.session.id)
        assert call.pending_authorization is None

    def test_confirm_payment_cancels_without_authorization(
        self, strongly_verified_ctx, temp_db, store
    ):
        """confirm_payment cancels when not authorized."""
        # First prepare a payment
        run(servicing_tools.prepare_payment(amount=923.33, tool_context=strongly_verified_ctx))

        # Then cancel it
        result = run(
            servicing_tools.confirm_payment(authorized=False, tool_context=strongly_verified_ctx)
        )
        assert result["result"] == "cancelled"

        # Authorization should be cleared
        call = store.call(strongly_verified_ctx.session.id)
        assert call.pending_authorization is None


# --- Data Model Tests ---


class TestLoanAccount:
    """Tests for LoanAccount dataclass."""

    def test_payoff_amount_includes_interest(self):
        """Payoff amount includes accrued interest."""
        loan = LoanAccount(
            id="TEST",
            customer_id="C1",
            customer_name="Test User",
            property_address="123 Test St",
            original_amount=Decimal("100000"),
            current_balance=Decimal("95000"),
            interest_rate=Decimal("6.00"),
            monthly_payment=Decimal("600"),
            loan_type="conventional",
            term_months=360,
            remaining_months=348,
            payment_day=1,
            next_due_date=date.today(),
            escrow_balance=Decimal("1000"),
            origination_date=date.today(),
            last_payment_date=date.today(),
        )

        # Payoff on same day should be close to balance
        payoff = loan.payoff_amount()
        assert payoff >= loan.current_balance

    def test_calculate_monthly_payment(self):
        """Monthly payment calculation is correct."""
        loan = LoanAccount(
            id="TEST",
            customer_id="C1",
            customer_name="Test User",
            property_address="123 Test St",
            original_amount=Decimal("100000"),
            current_balance=Decimal("100000"),
            interest_rate=Decimal("6.00"),
            monthly_payment=Decimal("0"),
            loan_type="conventional",
            term_months=360,
            remaining_months=360,
            payment_day=1,
            next_due_date=date.today(),
            escrow_balance=Decimal("0"),
            origination_date=date.today(),
        )

        payment = loan.calculate_monthly_payment()
        # For $100k at 6% over 30 years, payment should be ~$599.55
        assert Decimal("590") < payment < Decimal("610")


class TestDelinquencyStatus:
    """Tests for DelinquencyStatus."""

    def test_from_days_current(self):
        """0 DPD is current."""
        status = DelinquencyStatus.from_days("LN1", 0)
        assert status.stage == DelinquencyStage.CURRENT

    def test_from_days_early(self):
        """1-29 DPD is early stage."""
        status = DelinquencyStatus.from_days("LN1", 15)
        assert status.stage == DelinquencyStage.EARLY

    def test_from_days_moderate(self):
        """30-59 DPD is moderate."""
        status = DelinquencyStatus.from_days("LN1", 45)
        assert status.stage == DelinquencyStage.MODERATE

    def test_from_days_serious(self):
        """60-89 DPD is serious."""
        status = DelinquencyStatus.from_days("LN1", 75)
        assert status.stage == DelinquencyStage.SERIOUS

    def test_from_days_severe(self):
        """90+ DPD is severe."""
        status = DelinquencyStatus.from_days("LN1", 120)
        assert status.stage == DelinquencyStage.SEVERE
