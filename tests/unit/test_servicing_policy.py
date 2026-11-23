"""Tests for servicing policy enforcement."""
import asyncio
import tempfile
from pathlib import Path
from types import SimpleNamespace

import pytest

from mortgage_advisor.db.repositories import ServicingDatabase, use_servicing_db
from mortgage_advisor.services.origination import CallState, IdentityStrength, MortgageStore
from mortgage_advisor.agent import tools
from mortgage_advisor.agent.policy import (
    AGENT_TOOL_ACCESS,
    NEEDS_BASIC_VERIFICATION,
    NEEDS_STRONG_VERIFICATION,
    mortgage_gate,
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
    ctx = SimpleNamespace(session=SimpleNamespace(id="test-policy-call"))
    store.call(ctx.session.id)
    return ctx


class MockTool:
    """Mock tool for testing policy."""
    def __init__(self, name: str):
        self.name = name


# --- Verification Level Tests ---

class TestBasicVerificationRequired:
    """Tests for tools requiring basic verification."""

    def test_get_loan_balance_blocked_without_verification(self, ctx, store, temp_db):
        """get_loan_balance blocked without verification."""
        tool = MockTool("get_loan_balance")
        result = run(mortgage_gate(tool, {}, ctx))

        assert result is not None
        assert result["result"] == "blocked"
        assert result["code"] == "not_verified"

    def test_get_loan_balance_allowed_with_basic_verification(self, ctx, store, temp_db):
        """get_loan_balance allowed with basic verification."""
        call = store.call(ctx.session.id)
        call.verified_customer_id = "C1001"
        call.identity_strength = IdentityStrength.BASIC

        tool = MockTool("get_loan_balance")
        result = run(mortgage_gate(tool, {}, ctx))

        assert result is None  # None means allowed

    def test_all_basic_tools_require_verification(self):
        """All tools in NEEDS_BASIC_VERIFICATION are documented."""
        expected = {
            "get_loan_balance",
            "get_payment_history",
            "get_payoff_quote",
            "get_autopay_status",
            "get_payment_methods",
        }
        assert NEEDS_BASIC_VERIFICATION == expected


class TestStrongVerificationRequired:
    """Tests for tools requiring strong verification."""

    def test_change_payment_date_blocked_without_basic(self, ctx, store, temp_db):
        """change_payment_date blocked without any verification."""
        tool = MockTool("change_payment_date")
        result = run(mortgage_gate(tool, {"new_payment_day": 15}, ctx))

        assert result is not None
        assert result["result"] == "blocked"
        assert result["code"] == "not_verified"

    def test_change_payment_date_blocked_with_only_basic(self, ctx, store, temp_db):
        """change_payment_date blocked with only basic verification."""
        call = store.call(ctx.session.id)
        call.verified_customer_id = "C1001"
        call.identity_strength = IdentityStrength.BASIC

        tool = MockTool("change_payment_date")
        result = run(mortgage_gate(tool, {"new_payment_day": 15}, ctx))

        assert result is not None
        assert result["result"] == "blocked"
        assert result["code"] == "need_strong_verification"

    def test_change_payment_date_allowed_with_strong(self, ctx, store, temp_db):
        """change_payment_date allowed with strong verification."""
        call = store.call(ctx.session.id)
        call.verified_customer_id = "C1001"
        call.identity_strength = IdentityStrength.STRONG

        tool = MockTool("change_payment_date")
        result = run(mortgage_gate(tool, {"new_payment_day": 15}, ctx))

        assert result is None  # Allowed

    def test_all_strong_tools_require_verification(self):
        """All tools in NEEDS_STRONG_VERIFICATION are documented."""
        expected = {
            "change_payment_date",
            "setup_autopay",
            "cancel_autopay",
            "initiate_secure_card_capture",
            "complete_secure_card_capture",
            "add_bank_account",
            "set_default_payment_method",
            "remove_payment_method",
            "prepare_payment",
            "confirm_payment",
            "verify_customer_strong",
        }
        assert NEEDS_STRONG_VERIFICATION == expected


class TestPaymentConfirmation:
    """Tests for payment confirmation policy."""

    def test_confirm_payment_blocked_without_pending(self, ctx, store, temp_db):
        """confirm_payment blocked without pending authorization."""
        call = store.call(ctx.session.id)
        call.verified_customer_id = "C1001"
        call.identity_strength = IdentityStrength.STRONG

        tool = MockTool("confirm_payment")
        result = run(mortgage_gate(tool, {"authorized": True}, ctx))

        assert result is not None
        assert result["result"] == "blocked"
        assert result["code"] == "no_pending_payment"

    def test_confirm_payment_blocked_without_authorization_flag(self, ctx, store, temp_db):
        """confirm_payment blocked when authorized=False."""
        call = store.call(ctx.session.id)
        call.verified_customer_id = "C1001"
        call.identity_strength = IdentityStrength.STRONG
        call.pending_authorization = {"amount": 923.33}

        tool = MockTool("confirm_payment")
        result = run(mortgage_gate(tool, {"authorized": False}, ctx))

        assert result is not None
        assert result["result"] == "blocked"
        assert result["code"] == "not_authorized"

    def test_confirm_payment_allowed_when_authorized(self, ctx, store, temp_db):
        """confirm_payment allowed with pending auth and authorized=True."""
        call = store.call(ctx.session.id)
        call.verified_customer_id = "C1001"
        call.identity_strength = IdentityStrength.STRONG
        call.pending_authorization = {"amount": 923.33}

        tool = MockTool("confirm_payment")
        result = run(mortgage_gate(tool, {"authorized": True}, ctx))

        assert result is None  # Allowed


class TestAgentToolAccess:
    """Tests for agent-based tool access."""

    def test_origination_tools_defined(self):
        """Origination agent has expected tools."""
        tools = AGENT_TOOL_ACCESS["origination"]
        assert "get_company_info" in tools
        assert "check_heloc_eligibility" in tools
        assert "get_rate_estimate" in tools
        assert "verify_customer" in tools

    def test_servicing_tools_defined(self):
        """Servicing agent has expected tools."""
        tools = AGENT_TOOL_ACCESS["servicing"]
        assert "get_loan_balance" in tools
        assert "get_payment_history" in tools
        assert "setup_autopay" in tools
        assert "prepare_payment" in tools
        assert "verify_customer" in tools
        assert "verify_customer_strong" in tools

    def test_collections_tools_defined(self):
        """Collections agent has expected tools."""
        tools = AGENT_TOOL_ACCESS["collections"]
        assert "get_loan_balance" in tools
        assert "prepare_payment" in tools
        # Future: These will be added
        assert "request_forbearance" in tools
        assert "setup_payment_plan" in tools

    def test_no_cross_agent_sensitive_tools(self):
        """Origination can't access payment tools."""
        origination = AGENT_TOOL_ACCESS["origination"]
        assert "setup_autopay" not in origination
        assert "prepare_payment" not in origination
        assert "change_payment_date" not in origination


class TestCallStateMethods:
    """Tests for CallState verification methods."""

    def test_is_verified_basic_false_when_none(self, ctx, store):
        """is_verified_basic is False when identity_strength is none."""
        call = store.call(ctx.session.id)
        assert call.identity_strength == IdentityStrength.NONE
        assert call.is_verified_basic is False

    def test_is_verified_basic_true_when_basic(self, ctx, store):
        """is_verified_basic is True when identity_strength is basic."""
        call = store.call(ctx.session.id)
        call.identity_strength = IdentityStrength.BASIC
        assert call.is_verified_basic is True

    def test_is_verified_basic_true_when_strong(self, ctx, store):
        """is_verified_basic is True when identity_strength is strong."""
        call = store.call(ctx.session.id)
        call.identity_strength = IdentityStrength.STRONG
        assert call.is_verified_basic is True

    def test_is_verified_strong_false_when_basic(self, ctx, store):
        """is_verified_strong is False when identity_strength is basic."""
        call = store.call(ctx.session.id)
        call.identity_strength = IdentityStrength.BASIC
        assert call.is_verified_strong is False

    def test_is_verified_strong_true_when_strong(self, ctx, store):
        """is_verified_strong is True when identity_strength is strong."""
        call = store.call(ctx.session.id)
        call.identity_strength = IdentityStrength.STRONG
        assert call.is_verified_strong is True

    def test_clear_authorization(self, ctx, store):
        """clear_authorization clears pending state."""
        call = store.call(ctx.session.id)
        call.pending_authorization = {"amount": 100}
        call.authorization_confirmed = True

        call.clear_authorization()

        assert call.pending_authorization is None
        assert call.authorization_confirmed is False

    def test_clear_secure_capture(self, ctx, store):
        """clear_secure_capture clears capture state."""
        call = store.call(ctx.session.id)
        call.secure_capture_pending = True
        call.secure_capture_type = "card"

        call.clear_secure_capture()

        assert call.secure_capture_pending is False
        assert call.secure_capture_type is None
