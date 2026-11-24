"""Tests for option comparison, payment calculations, and rate sheet lookups."""

import asyncio
from datetime import datetime
from types import SimpleNamespace

import pytest

from mortgage.mortgage import MortgageError, MortgageStore

# --- Fixtures ---


@pytest.fixture
def store_with_rates():
    """Create a store with a complete rate sheet for testing."""
    seed = {
        "company": {
            "name": "Test Mortgage Co",
            "phone": "555-1234",
            "address": "123 Test St",
            "hours": {"mon": ["09:00", "17:00"]},
            "disclaimers": {"rates": "Rates subject to change."},
        },
        "products": {
            "heloc": {
                "name": "HELOC",
                "description": "Home Equity Line of Credit",
                "rate_range": [7.0, 10.0],
            },
            "cash_out_refi": {
                "name": "Cash-Out Refinance",
                "description": "Cash-out refinance",
                "rate_range": [6.0, 8.0],
            },
            "rate_term_refi": {
                "name": "Rate-Term Refinance",
                "description": "Rate and term refinance",
                "rate_range": [5.5, 7.5],
            },
        },
        "state_regulations": {
            "TX": {
                "heloc_rules": {
                    "max_cltv": 80,
                    "allowed_on_investment": False,
                    "allowed_with_existing_cashout": False,  # TX Constitution: no HELOC after cash-out
                    "closing_notice_days": 12,
                    "rescission_days": 3,
                },
                "cashout_rules": {
                    "max_ltv": 80,
                    "once_per_year": True,  # TX Constitution: once per 12 months
                },
            },
            "CA": {
                "heloc_rules": {"max_cltv": 90, "allowed_on_investment": True},
                "cashout_rules": {
                    "max_ltv": 85  # Higher LTV allowed in CA
                },
            },
        },
        "loan_officers": [],
        "customers": [],
    }

    rate_sheet = {
        "as_of": "2026-10-05",
        "credit_tiers": {
            "excellent": {"min": 760, "max": 850},
            "good": {"min": 720, "max": 759},
            "fair": {"min": 680, "max": 719},
            "below_average": {"min": 640, "max": 679},
            "poor": {"min": 300, "max": 639},
        },
        "ltv_bands": {
            "low": {"min": 0, "max": 60},
            "moderate": {"min": 61, "max": 75},
            "standard": {"min": 76, "max": 80},
            "high": {"min": 81, "max": 90},
            "very_high": {"min": 91, "max": 100},
        },
        "products": {
            "heloc": {
                "name": "Home Equity Line of Credit",
                "rates": {
                    "excellent": {
                        "low": 7.25,
                        "moderate": 7.5,
                        "standard": 7.75,
                        "high": None,
                        "very_high": None,
                    },
                    "good": {
                        "low": 7.75,
                        "moderate": 8.0,
                        "standard": 8.25,
                        "high": None,
                        "very_high": None,
                    },
                    "fair": {
                        "low": 8.25,
                        "moderate": 8.5,
                        "standard": 8.75,
                        "high": None,
                        "very_high": None,
                    },
                },
                "market_benchmark": {"rate": 8.75, "source": "Test Index"},
            },
            "cash_out_refi": {
                "name": "Cash-Out Refinance",
                "term_years": 30,
                "rates": {
                    "excellent": {
                        "low": 6.125,
                        "moderate": 6.25,
                        "standard": 6.375,
                        "high": 6.625,
                        "very_high": None,
                    },
                    "good": {
                        "low": 6.375,
                        "moderate": 6.5,
                        "standard": 6.625,
                        "high": 6.875,
                        "very_high": None,
                    },
                },
                "market_benchmark": {"rate": 7.0, "source": "Test Index"},
            },
            "rate_term_refi": {
                "name": "Rate-and-Term Refinance",
                "term_years": 30,
                "rates": {
                    "excellent": {
                        "low": 5.75,
                        "moderate": 5.875,
                        "standard": 6.0,
                        "high": 6.25,
                        "very_high": 6.5,
                    },
                    "good": {
                        "low": 6.0,
                        "moderate": 6.125,
                        "standard": 6.25,
                        "high": 6.5,
                        "very_high": 6.75,
                    },
                },
                "market_benchmark": {"rate": 6.5, "source": "Test Index"},
            },
        },
    }

    return MortgageStore(seed, rate_sheet=rate_sheet)


# --- Payment Calculation Tests ---


class TestMonthlyPaymentCalculation:
    """Tests for calculate_monthly_payment static method."""

    def test_standard_30_year_mortgage(self, store_with_rates):
        """Calculate payment for a standard 30-year mortgage."""
        # $300,000 at 6% for 30 years = ~$1,798.65
        payment = store_with_rates.calculate_monthly_payment(300000, 6.0, 30)
        assert 1798 <= payment <= 1800

    def test_15_year_mortgage(self, store_with_rates):
        """Calculate payment for a 15-year mortgage."""
        # $300,000 at 5.5% for 15 years = ~$2,451.55
        payment = store_with_rates.calculate_monthly_payment(300000, 5.5, 15)
        assert 2451 <= payment <= 2452

    def test_zero_principal_returns_zero(self, store_with_rates):
        """Zero principal should return zero payment."""
        payment = store_with_rates.calculate_monthly_payment(0, 6.0, 30)
        assert payment == 0.0

    def test_zero_rate_returns_zero(self, store_with_rates):
        """Zero rate should return zero."""
        payment = store_with_rates.calculate_monthly_payment(300000, 0, 30)
        assert payment == 0.0

    def test_negative_values_return_zero(self, store_with_rates):
        """Negative values should return zero."""
        assert store_with_rates.calculate_monthly_payment(-100000, 6.0, 30) == 0.0
        assert store_with_rates.calculate_monthly_payment(100000, -6.0, 30) == 0.0
        assert store_with_rates.calculate_monthly_payment(100000, 6.0, -30) == 0.0


# --- Credit Tier Tests ---


class TestCreditTierLookup:
    """Tests for get_credit_tier method."""

    def test_excellent_tier(self, store_with_rates):
        """Scores 760-850 are excellent."""
        assert store_with_rates.get_credit_tier(760) == "excellent"
        assert store_with_rates.get_credit_tier(800) == "excellent"
        assert store_with_rates.get_credit_tier(850) == "excellent"

    def test_good_tier(self, store_with_rates):
        """Scores 720-759 are good."""
        assert store_with_rates.get_credit_tier(720) == "good"
        assert store_with_rates.get_credit_tier(740) == "good"
        assert store_with_rates.get_credit_tier(759) == "good"

    def test_fair_tier(self, store_with_rates):
        """Scores 680-719 are fair."""
        assert store_with_rates.get_credit_tier(680) == "fair"
        assert store_with_rates.get_credit_tier(700) == "fair"
        assert store_with_rates.get_credit_tier(719) == "fair"

    def test_below_average_tier(self, store_with_rates):
        """Scores 640-679 are below_average."""
        assert store_with_rates.get_credit_tier(640) == "below_average"
        assert store_with_rates.get_credit_tier(660) == "below_average"
        assert store_with_rates.get_credit_tier(679) == "below_average"

    def test_poor_tier(self, store_with_rates):
        """Scores 300-639 are poor."""
        assert store_with_rates.get_credit_tier(300) == "poor"
        assert store_with_rates.get_credit_tier(500) == "poor"
        assert store_with_rates.get_credit_tier(639) == "poor"

    def test_no_rate_sheet_returns_none(self):
        """No rate sheet returns None."""
        seed = {
            "company": {"name": "Test", "phone": "", "address": "", "hours": {}, "disclaimers": {}},
            "products": {},
            "loan_officers": [],
        }
        store = MortgageStore(seed)
        assert store.get_credit_tier(750) is None


# --- LTV Band Tests ---


class TestLtvBandLookup:
    """Tests for get_ltv_band method."""

    def test_low_band(self, store_with_rates):
        """LTV 0-60% is low."""
        assert store_with_rates.get_ltv_band(0) == "low"
        assert store_with_rates.get_ltv_band(30) == "low"
        assert store_with_rates.get_ltv_band(60) == "low"

    def test_moderate_band(self, store_with_rates):
        """LTV 61-75% is moderate."""
        assert store_with_rates.get_ltv_band(61) == "moderate"
        assert store_with_rates.get_ltv_band(70) == "moderate"
        assert store_with_rates.get_ltv_band(75) == "moderate"

    def test_standard_band(self, store_with_rates):
        """LTV 76-80% is standard."""
        assert store_with_rates.get_ltv_band(76) == "standard"
        assert store_with_rates.get_ltv_band(78) == "standard"
        assert store_with_rates.get_ltv_band(80) == "standard"

    def test_high_band(self, store_with_rates):
        """LTV 81-90% is high."""
        assert store_with_rates.get_ltv_band(81) == "high"
        assert store_with_rates.get_ltv_band(85) == "high"
        assert store_with_rates.get_ltv_band(90) == "high"

    def test_very_high_band(self, store_with_rates):
        """LTV 91-100% is very_high."""
        assert store_with_rates.get_ltv_band(91) == "very_high"
        assert store_with_rates.get_ltv_band(95) == "very_high"
        assert store_with_rates.get_ltv_band(100) == "very_high"


# --- Rate Sheet Lookup Tests ---


class TestRateFromSheet:
    """Tests for get_rate_from_sheet method."""

    def test_excellent_low_ltv_heloc(self, store_with_rates):
        """Excellent credit + low LTV gets best HELOC rate."""
        result = store_with_rates.get_rate_from_sheet("heloc", 800, 50)
        assert result is not None
        assert result["rate"] == 7.25
        assert result["credit_tier"] == "excellent"
        assert result["ltv_band"] == "low"

    def test_good_moderate_ltv(self, store_with_rates):
        """Good credit + moderate LTV."""
        result = store_with_rates.get_rate_from_sheet("heloc", 730, 70)
        assert result is not None
        assert result["rate"] == 8.0
        assert result["credit_tier"] == "good"
        assert result["ltv_band"] == "moderate"

    def test_unavailable_combination_returns_none(self, store_with_rates):
        """HELOC not available at high LTV."""
        result = store_with_rates.get_rate_from_sheet("heloc", 800, 85)
        # Rate is None in the sheet for high LTV HELOC
        assert result is None

    def test_unknown_product_returns_none(self, store_with_rates):
        """Unknown product returns None."""
        result = store_with_rates.get_rate_from_sheet("unknown_product", 750, 75)
        assert result is None

    def test_benchmark_included(self, store_with_rates):
        """Market benchmark is included in result."""
        result = store_with_rates.get_rate_from_sheet("heloc", 800, 50)
        assert result["benchmark"]["rate"] == 8.75


# --- Rate Estimate Tests ---


class TestRateEstimate:
    """Tests for get_rate_estimate using rate sheet."""

    def test_uses_rate_sheet_when_available(self, store_with_rates):
        """get_rate_estimate uses rate sheet rates."""
        result = store_with_rates.get_rate_estimate("heloc", 800, 50)
        assert result["estimated_rate"] == 7.25
        assert result["credit_tier"] == "excellent"
        assert result["market_benchmark"] == 8.75

    def test_includes_benchmark_comparison(self, store_with_rates):
        """Result includes market benchmark for comparison."""
        result = store_with_rates.get_rate_estimate("cash_out_refi", 800, 60)
        assert "market_benchmark" in result
        assert result["market_benchmark"] == 7.0

    def test_falls_back_to_product_range(self, store_with_rates):
        """Falls back to product rate_range when sheet unavailable."""
        # Poor credit at high LTV - not in rate sheet
        result = store_with_rates.get_rate_estimate("heloc", 600, 85)
        # Should fall back to product rate_range with adjustments
        assert "estimated_rate" in result
        assert "rate_range" in result


# --- Compare Options Tests ---


class TestCompareOptions:
    """Tests for compare_options method."""

    def test_california_eligible_for_heloc(self, store_with_rates):
        """California property eligible for HELOC."""
        result = store_with_rates.compare_options(
            property_value=500000,
            current_balance=200000,
            credit_score=750,
            state="CA",
            property_use="primary",
            has_existing_cashout=False,
        )
        assert result["state"] == "CA"
        assert len(result["options"]) > 0
        # Should have HELOC option since CA allows it
        heloc_options = [o for o in result["options"] if o["product"] == "heloc"]
        assert len(heloc_options) > 0

    def test_texas_heloc_at_80_ltv_blocked(self, store_with_rates):
        """Texas HELOC blocked when at 80% LTV."""
        result = store_with_rates.compare_options(
            property_value=500000,
            current_balance=400000,  # 80% LTV
            credit_score=750,
            state="TX",
            property_use="primary",
            has_existing_cashout=False,
        )
        assert result["state"] == "TX"
        # HELOC should not be available - in excluded list
        heloc_options = [o for o in result["options"] if o["product"] == "heloc"]
        assert len(heloc_options) == 0
        # Should have heloc_issues or excluded
        has_heloc_issue = (result.get("heloc_issues") and len(result["heloc_issues"]) > 0) or (
            result.get("excluded") and any(e["product"] == "heloc" for e in result["excluded"])
        )
        assert has_heloc_issue

    def test_includes_cash_out_option(self, store_with_rates):
        """Cash-out refinance option included when LTV allows."""
        result = store_with_rates.compare_options(
            property_value=500000,
            current_balance=200000,
            credit_score=750,
            state="CA",
            property_use="primary",
            has_existing_cashout=False,
            cash_needed=50000,
        )
        cashout_options = [o for o in result["options"] if o["product"] == "cash_out_refi"]
        assert len(cashout_options) > 0
        opt = cashout_options[0]
        assert "monthly_payment" in opt
        assert opt["amount"] == 250000  # 200k + 50k

    def test_includes_rate_term_refi_when_no_cash(self, store_with_rates):
        """Rate-term refi included when cash_needed is 0."""
        result = store_with_rates.compare_options(
            property_value=500000,
            current_balance=300000,
            credit_score=750,
            state="CA",
            property_use="primary",
            has_existing_cashout=False,
            cash_needed=0,
        )
        refi_options = [o for o in result["options"] if o["product"] == "rate_term_refi"]
        assert len(refi_options) > 0

    def test_no_rate_term_refi_when_cash_needed(self, store_with_rates):
        """Rate-term refi not included when cash_needed > 0."""
        result = store_with_rates.compare_options(
            property_value=500000,
            current_balance=200000,
            credit_score=750,
            state="CA",
            property_use="primary",
            has_existing_cashout=False,
            cash_needed=50000,
        )
        refi_options = [o for o in result["options"] if o["product"] == "rate_term_refi"]
        assert len(refi_options) == 0

    def test_savings_vs_market_calculated(self, store_with_rates):
        """Savings vs market benchmark calculated when rate is lower."""
        result = store_with_rates.compare_options(
            property_value=500000,
            current_balance=200000,
            credit_score=800,  # Excellent credit
            state="CA",
            property_use="primary",
            has_existing_cashout=False,
        )
        # Some options should show savings vs market
        options_with_savings = [o for o in result["options"] if "savings_vs_market" in o]
        # With excellent credit, rates should be below benchmark
        assert len(options_with_savings) > 0

    def test_unknown_state_raises_error(self, store_with_rates):
        """Unknown state raises MortgageError."""
        with pytest.raises(MortgageError) as exc:
            store_with_rates.compare_options(
                property_value=500000,
                current_balance=200000,
                credit_score=750,
                state="ZZ",
                property_use="primary",
                has_existing_cashout=False,
            )
        assert exc.value.code == "unknown_state"

    def test_state_without_rules_shows_needs_review(self, store_with_rates):
        """State without rules on file shows needs_review."""
        # Add a state with no heloc_rules
        store_with_rates.state_regulations["FL"] = {}

        result = store_with_rates.compare_options(
            property_value=500000,
            current_balance=200000,
            credit_score=750,
            state="FL",
            property_use="primary",
            has_existing_cashout=False,
        )
        # Should indicate needs review status or have HELOC in excluded list
        has_issue = result.get("status") == "needs_review" or any(
            e["product"] == "heloc" and "not on file" in e["reason"].lower()
            for e in result.get("excluded", [])
        )
        assert has_issue

    def test_equity_calculation(self, store_with_rates):
        """Equity is correctly calculated."""
        result = store_with_rates.compare_options(
            property_value=500000,
            current_balance=200000,
            credit_score=750,
            state="CA",
            property_use="primary",
            has_existing_cashout=False,
        )
        assert result["equity"] == 300000
        assert result["current_ltv"] == 40.0


# --- Policy Door Tests for compare_options ---


class TestCompareOptionsPolicy:
    """Tests for policy door validation of compare_options."""

    @pytest.fixture
    def mock_tool_context(self, store_with_rates):
        """Create mock tool context."""
        from mortgage import tools

        tools.use_store(store_with_rates)
        return SimpleNamespace(session=SimpleNamespace(id="test-session-123"))

    @pytest.fixture
    def mock_tool(self):
        """Create mock tool."""
        return SimpleNamespace(name="compare_options")

    def test_blocks_unknown_state(self, mock_tool, mock_tool_context):
        """Blocks when state is unrecognized."""
        from mortgage.policy import mortgage_gate

        args = {
            "state": "ZZ",
            "property_value": 500000,
            "current_mortgage_balance": 200000,
            "credit_score": 750,
            "property_use": "primary",
            "has_existing_cashout": False,
        }

        result = asyncio.run(mortgage_gate(mock_tool, args, mock_tool_context))
        assert result is not None
        assert result["result"] == "blocked"
        assert result["code"] == "unknown_state"

    def test_blocks_state_without_regulations(self, mock_tool, mock_tool_context, store_with_rates):
        """Blocks when state has no regulations on file."""
        from mortgage.policy import mortgage_gate

        # NY is a valid state but has no regulations in our test data
        args = {
            "state": "NY",
            "property_value": 500000,
            "current_mortgage_balance": 200000,
            "credit_score": 750,
            "property_use": "primary",
            "has_existing_cashout": False,
        }

        result = asyncio.run(mortgage_gate(mock_tool, args, mock_tool_context))
        assert result is not None
        assert result["result"] == "blocked"
        assert result["code"] == "unknown_state"
        assert "No regulations on file" in result["reason"]

    def test_blocks_invalid_credit_score(self, mock_tool, mock_tool_context):
        """Blocks when credit score is out of range."""
        from mortgage.policy import mortgage_gate

        args = {
            "state": "TX",
            "property_value": 500000,
            "current_mortgage_balance": 200000,
            "credit_score": 900,  # Invalid
            "property_use": "primary",
            "has_existing_cashout": False,
        }

        result = asyncio.run(mortgage_gate(mock_tool, args, mock_tool_context))
        assert result is not None
        assert result["result"] == "blocked"
        assert result["code"] == "missing_inputs"

    def test_blocks_zero_property_value(self, mock_tool, mock_tool_context):
        """Blocks when property value is zero or negative."""
        from mortgage.policy import mortgage_gate

        args = {
            "state": "TX",
            "property_value": 0,
            "current_mortgage_balance": 200000,
            "credit_score": 750,
            "property_use": "primary",
            "has_existing_cashout": False,
        }

        result = asyncio.run(mortgage_gate(mock_tool, args, mock_tool_context))
        assert result is not None
        assert result["result"] == "blocked"
        assert result["code"] == "missing_inputs"

    def test_allows_valid_request(self, mock_tool, mock_tool_context):
        """Allows valid compare_options request."""
        from mortgage.policy import mortgage_gate

        args = {
            "state": "TX",
            "property_value": 500000,
            "current_mortgage_balance": 200000,
            "credit_score": 750,
            "property_use": "primary",
            "has_existing_cashout": False,
        }

        result = asyncio.run(mortgage_gate(mock_tool, args, mock_tool_context))
        assert result is None  # None means allowed


# --- Tool Integration Tests ---


class TestCompareOptionsTool:
    """Tests for compare_options tool function."""

    @pytest.fixture
    def setup_store(self, store_with_rates):
        """Set up the store for tool tests."""
        from mortgage import tools

        tools.use_store(store_with_rates)
        yield

    def test_tool_returns_formatted_response(self, setup_store):
        """Tool returns properly formatted response."""
        from mortgage.tools import compare_options

        result = asyncio.run(
            compare_options(
                state="CA",
                property_value=500000,
                current_mortgage_balance=200000,
                credit_score=750,
                property_use="primary",
                has_existing_cashout=False,
            )
        )

        assert result["result"] == "ok"
        assert "options" in result
        assert "disclaimer" in result
        assert "say" in result

    def test_tool_formats_currency(self, setup_store):
        """Tool formats currency values."""
        from mortgage.tools import compare_options

        result = asyncio.run(
            compare_options(
                state="CA",
                property_value=500000,
                current_mortgage_balance=200000,
                credit_score=750,
                property_use="primary",
                has_existing_cashout=False,
            )
        )

        assert "$" in result["property_value"]
        assert "$" in result["equity"]

    def test_tool_formats_rates(self, setup_store):
        """Tool formats rate percentages."""
        from mortgage.tools import compare_options

        result = asyncio.run(
            compare_options(
                state="CA",
                property_value=500000,
                current_mortgage_balance=200000,
                credit_score=750,
                property_use="primary",
                has_existing_cashout=False,
            )
        )

        for opt in result["options"]:
            assert "%" in opt["rate"]

    def test_tool_handles_error(self, setup_store):
        """Tool handles MortgageError gracefully."""
        from mortgage.tools import compare_options

        result = asyncio.run(
            compare_options(
                state="ZZ",  # Invalid
                property_value=500000,
                current_mortgage_balance=200000,
                credit_score=750,
                property_use="primary",
                has_existing_cashout=False,
            )
        )

        assert result["result"] == "error"
        assert result["code"] == "unknown_state"


# --- N1 Critical Tests: Eligibility Rules ---


class TestCompareOptionsEligibility:
    """Tests for compare_options eligibility rules - N1 critical fix."""

    def test_texas_existing_cashout_excludes_heloc(self, store_with_rates):
        """TX + existing cash-out mortgage = NO HELOC (Texas Constitution)."""
        result = store_with_rates.compare_options(
            property_value=550000,
            current_balance=100000,
            credit_score=750,
            state="TX",
            property_use="primary",
            has_existing_cashout=True,  # Has existing cash-out
            cash_needed=40000,
        )

        # HELOC should NOT be in options
        heloc_options = [o for o in result["options"] if o["product"] == "heloc"]
        assert (
            len(heloc_options) == 0
        ), "HELOC should be excluded when has_existing_cashout=True in TX"

        # HELOC should be in excluded list with reason
        assert "excluded" in result
        heloc_excluded = [e for e in result["excluded"] if e["product"] == "heloc"]
        assert len(heloc_excluded) > 0, "HELOC should be in excluded list"
        assert "cash-out" in heloc_excluded[0]["reason"].lower()

    def test_texas_no_cashout_allows_heloc(self, store_with_rates):
        """TX without existing cash-out CAN get HELOC (if LTV allows)."""
        result = store_with_rates.compare_options(
            property_value=550000,
            current_balance=100000,  # ~18% LTV, well under 80%
            credit_score=750,
            state="TX",
            property_use="primary",
            has_existing_cashout=False,
        )

        # HELOC should be available
        heloc_options = [o for o in result["options"] if o["product"] == "heloc"]
        assert len(heloc_options) > 0, "HELOC should be available without existing cash-out in TX"

    def test_california_existing_cashout_allows_heloc(self, store_with_rates):
        """CA allows HELOC even with existing cash-out (no TX Constitution restriction)."""
        result = store_with_rates.compare_options(
            property_value=550000,
            current_balance=100000,
            credit_score=750,
            state="CA",
            property_use="primary",
            has_existing_cashout=True,  # Has existing cash-out, but CA allows this
        )

        # HELOC should still be available in CA
        heloc_options = [o for o in result["options"] if o["product"] == "heloc"]
        assert len(heloc_options) > 0, "HELOC should be available in CA even with existing cash-out"

    def test_texas_investment_property_excludes_heloc(self, store_with_rates):
        """TX + investment property = NO HELOC."""
        result = store_with_rates.compare_options(
            property_value=550000,
            current_balance=100000,
            credit_score=750,
            state="TX",
            property_use="investment",  # Investment property
            has_existing_cashout=False,
        )

        # HELOC should NOT be in options
        heloc_options = [o for o in result["options"] if o["product"] == "heloc"]
        assert len(heloc_options) == 0, "HELOC should be excluded for investment property in TX"

        # Should be in excluded list
        assert "excluded" in result
        heloc_excluded = [e for e in result["excluded"] if e["product"] == "heloc"]
        assert len(heloc_excluded) > 0

    def test_cashout_once_per_year_excludes_recent(self, store_with_rates):
        """TX cash-out within 365 days = NO new cash-out (once per year rule)."""
        from datetime import timedelta

        # Cash-out done 6 months ago
        recent_date = (datetime.now() - timedelta(days=180)).strftime("%Y-%m-%d")

        result = store_with_rates.compare_options(
            property_value=550000,
            current_balance=100000,
            credit_score=750,
            state="TX",
            property_use="primary",
            has_existing_cashout=False,
            last_cashout_date=recent_date,  # Within 1 year
        )

        # Cash-out should NOT be in options
        cashout_options = [o for o in result["options"] if o["product"] == "cash_out_refi"]
        assert (
            len(cashout_options) == 0
        ), "Cash-out should be excluded within 365 days of last cash-out in TX"

        # Should be in excluded list
        assert "excluded" in result
        cashout_excluded = [e for e in result["excluded"] if e["product"] == "cash_out_refi"]
        assert len(cashout_excluded) > 0
        reason = cashout_excluded[0]["reason"].lower()
        assert "12 months" in reason or "year" in reason or "365" in reason

    def test_cashout_once_per_year_allows_old(self, store_with_rates):
        """TX cash-out more than 365 days ago = cash-out IS allowed."""
        from datetime import timedelta

        # Cash-out done 400 days ago
        old_date = (datetime.now() - timedelta(days=400)).strftime("%Y-%m-%d")

        result = store_with_rates.compare_options(
            property_value=550000,
            current_balance=100000,
            credit_score=750,
            state="TX",
            property_use="primary",
            has_existing_cashout=False,
            last_cashout_date=old_date,  # More than 1 year ago
            cash_needed=50000,
        )

        # Cash-out should be available
        cashout_options = [o for o in result["options"] if o["product"] == "cash_out_refi"]
        assert (
            len(cashout_options) > 0
        ), "Cash-out should be available after 365 days since last cash-out"

    def test_uses_state_specific_cashout_max_ltv(self, store_with_rates):
        """Uses state's cashout_rules.max_ltv instead of hardcoded 80."""
        # CA has max_ltv: 85, TX has max_ltv: 80
        # At 82% LTV: CA should allow cash-out, TX should block

        # 82% LTV scenario
        property_value = 500000
        current_balance = 360000  # 72% LTV
        cash_needed = 50000  # Would result in 82% new LTV

        # California should allow (85% max)
        result_ca = store_with_rates.compare_options(
            property_value=property_value,
            current_balance=current_balance,
            credit_score=750,
            state="CA",
            property_use="primary",
            has_existing_cashout=False,
            cash_needed=cash_needed,
        )
        cashout_ca = [o for o in result_ca["options"] if o["product"] == "cash_out_refi"]
        assert len(cashout_ca) > 0, "CA should allow cash-out at 82% LTV (max is 85%)"

        # Texas should block (80% max)
        result_tx = store_with_rates.compare_options(
            property_value=property_value,
            current_balance=current_balance,
            credit_score=750,
            state="TX",
            property_use="primary",
            has_existing_cashout=False,
            cash_needed=cash_needed,
        )
        cashout_tx = [o for o in result_tx["options"] if o["product"] == "cash_out_refi"]
        assert len(cashout_tx) == 0, "TX should block cash-out at 82% LTV (max is 80%)"

    def test_excluded_list_has_reasons(self, store_with_rates):
        """Excluded options include clear reasons."""
        result = store_with_rates.compare_options(
            property_value=550000,
            current_balance=100000,
            credit_score=750,
            state="TX",
            property_use="investment",  # Will exclude HELOC
            has_existing_cashout=True,  # Would also exclude HELOC
        )

        assert "excluded" in result
        assert len(result["excluded"]) > 0

        for excluded in result["excluded"]:
            assert "product" in excluded
            assert "reason" in excluded
            assert len(excluded["reason"]) > 0


class TestCompareOptionsPolicyValidation:
    """Tests for policy door validation of compare_options - N1 critical fix."""

    @pytest.fixture
    def mock_tool_context(self, store_with_rates):
        """Create mock tool context."""
        from mortgage import tools

        tools.use_store(store_with_rates)
        return SimpleNamespace(session=SimpleNamespace(id="test-session-456"))

    @pytest.fixture
    def mock_tool(self):
        """Create mock tool."""
        return SimpleNamespace(name="compare_options")

    def test_blocks_missing_property_use(self, mock_tool, mock_tool_context):
        """Blocks when property_use is not provided."""
        from mortgage.policy import mortgage_gate

        args = {
            "state": "TX",
            "property_value": 500000,
            "current_mortgage_balance": 200000,
            "credit_score": 750,
            # property_use NOT provided
            "has_existing_cashout": False,
        }

        result = asyncio.run(mortgage_gate(mock_tool, args, mock_tool_context))
        assert result is not None
        assert result["result"] == "blocked"
        assert result["code"] == "missing_inputs"
        assert "property_use" in result["reason"]

    def test_blocks_missing_has_existing_cashout(self, mock_tool, mock_tool_context):
        """Blocks when has_existing_cashout is not provided."""
        from mortgage.policy import mortgage_gate

        args = {
            "state": "TX",
            "property_value": 500000,
            "current_mortgage_balance": 200000,
            "credit_score": 750,
            "property_use": "primary",
            # has_existing_cashout NOT provided
        }

        result = asyncio.run(mortgage_gate(mock_tool, args, mock_tool_context))
        assert result is not None
        assert result["result"] == "blocked"
        assert result["code"] == "missing_inputs"
        assert "has_existing_cashout" in result["reason"]

    def test_allows_with_all_required_params(self, mock_tool, mock_tool_context):
        """Allows when all required parameters provided."""
        from mortgage.policy import mortgage_gate

        args = {
            "state": "TX",
            "property_value": 500000,
            "current_mortgage_balance": 200000,
            "credit_score": 750,
            "property_use": "primary",
            "has_existing_cashout": False,
        }

        result = asyncio.run(mortgage_gate(mock_tool, args, mock_tool_context))
        assert result is None  # None means allowed

    def test_allows_various_property_use_values(self, mock_tool, mock_tool_context):
        """Allows various property_use values (normalization happens in tool)."""
        from mortgage.policy import mortgage_gate

        for property_use in [
            "primary",
            "my home",
            "rental",
            "investment property",
            "vacation home",
        ]:
            args = {
                "state": "TX",
                "property_value": 500000,
                "current_mortgage_balance": 200000,
                "credit_score": 750,
                "property_use": property_use,
                "has_existing_cashout": False,
            }

            result = asyncio.run(mortgage_gate(mock_tool, args, mock_tool_context))
            assert result is None, f"Should allow property_use='{property_use}'"
