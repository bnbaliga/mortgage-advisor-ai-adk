"""Loan servicing data models — active loans, payments, autopay, delinquency.

These dataclasses represent the servicing lifecycle after origination:
- LoanAccount: Active loan with balance, rate, payment schedule
- PaymentHistory: Record of payments made
- PaymentSchedule: Due dates and amounts
- PaymentMethod: Tokenized payment methods (cards, bank accounts)
- DelinquencyStatus: Days past due, collections stage

All data is stored in SQLite via database.py. No network: the voice agent's
tools are thin wrappers over `ServicingDatabase`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from enum import Enum


class PaymentStatus(Enum):
    """Status of a scheduled payment."""

    SCHEDULED = "scheduled"
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    LATE = "late"
    PARTIAL = "partial"


class PaymentMethodType(Enum):
    """Type of payment method."""

    CHECKING = "checking"
    SAVINGS = "savings"
    DEBIT_CARD = "debit_card"
    CREDIT_CARD = "credit_card"


class DelinquencyStage(Enum):
    """Collections stage based on days past due."""

    CURRENT = "current"  # 0 DPD
    EARLY = "early"  # 1-29 DPD - reminders
    MODERATE = "moderate"  # 30-59 DPD - outreach
    SERIOUS = "serious"  # 60-89 DPD - collections
    SEVERE = "severe"  # 90+ DPD - loss mitigation


class LossMitigationStatus(Enum):
    """Status of loss mitigation request."""

    NONE = "none"
    REQUESTED = "requested"
    IN_REVIEW = "in_review"
    APPROVED = "approved"
    DENIED = "denied"
    ACTIVE = "active"


@dataclass
class PaymentMethod:
    """Tokenized payment method on file.

    Card numbers are NEVER stored - only tokens from secure capture.
    """

    id: str
    customer_id: str
    method_type: PaymentMethodType
    last_four: str  # Last 4 digits for display
    institution_name: str  # Bank name or card network
    nickname: str | None  # Customer-assigned nickname
    is_default: bool = False
    is_autopay: bool = False  # Used for autopay
    token: str = ""  # Secure payment token (mock)
    expiration_date: str | None = None  # MM/YY for cards
    created_at: datetime = field(default_factory=datetime.now)

    def display_name(self) -> str:
        """Human-readable description of this payment method."""
        if self.nickname:
            return f"{self.nickname} (...{self.last_four})"
        type_name = self.method_type.value.replace("_", " ").title()
        return f"{self.institution_name} {type_name} (...{self.last_four})"


@dataclass
class PaymentSchedule:
    """A scheduled payment - past, current, or future."""

    id: str
    loan_id: str
    due_date: date
    principal_amount: Decimal
    interest_amount: Decimal
    escrow_amount: Decimal  # Taxes + insurance
    total_amount: Decimal
    status: PaymentStatus = PaymentStatus.SCHEDULED
    paid_date: date | None = None
    paid_amount: Decimal | None = None
    payment_method_id: str | None = None
    confirmation_number: str | None = None

    @property
    def is_past_due(self) -> bool:
        """Check if this payment is past due."""
        if self.status == PaymentStatus.COMPLETED:
            return False
        return self.due_date < date.today()

    @property
    def days_past_due(self) -> int:
        """Days past the due date (0 if not past due)."""
        if not self.is_past_due:
            return 0
        return (date.today() - self.due_date).days


@dataclass
class PaymentHistory:
    """Record of a payment made."""

    id: str
    loan_id: str
    payment_date: date
    amount: Decimal
    principal_applied: Decimal
    interest_applied: Decimal
    escrow_applied: Decimal
    payment_method_id: str
    payment_method_last_four: str
    status: PaymentStatus
    confirmation_number: str
    posted_date: date | None = None
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class DelinquencyStatus:
    """Delinquency and loss mitigation status for a loan."""

    loan_id: str
    days_past_due: int = 0
    stage: DelinquencyStage = DelinquencyStage.CURRENT
    amount_past_due: Decimal = Decimal("0.00")
    payments_missed: int = 0
    last_payment_date: date | None = None
    loss_mitigation_status: LossMitigationStatus = LossMitigationStatus.NONE
    forbearance_end_date: date | None = None
    payment_plan_id: str | None = None

    @classmethod
    def from_days(
        cls, loan_id: str, dpd: int, amount: Decimal = Decimal("0.00")
    ) -> DelinquencyStatus:
        """Create delinquency status from days past due."""
        if dpd == 0:
            stage = DelinquencyStage.CURRENT
        elif dpd < 30:
            stage = DelinquencyStage.EARLY
        elif dpd < 60:
            stage = DelinquencyStage.MODERATE
        elif dpd < 90:
            stage = DelinquencyStage.SERIOUS
        else:
            stage = DelinquencyStage.SEVERE

        return cls(
            loan_id=loan_id,
            days_past_due=dpd,
            stage=stage,
            amount_past_due=amount,
            payments_missed=(dpd + 29) // 30 if dpd > 0 else 0,
        )


@dataclass
class LoanAccount:
    """An active loan in servicing.

    This represents a loan after closing - the servicing phase of the lifecycle.
    """

    id: str
    customer_id: str
    customer_name: str
    property_address: str

    # Loan details
    original_amount: Decimal
    current_balance: Decimal
    interest_rate: Decimal  # Annual rate as percentage
    monthly_payment: Decimal  # P&I + escrow
    loan_type: str  # conventional, fha, va, etc.
    term_months: int  # Original term
    remaining_months: int

    # Payment info
    payment_day: int  # Day of month (1-28)
    next_due_date: date
    escrow_balance: Decimal  # Escrowed taxes/insurance

    # Autopay
    autopay_enabled: bool = False
    autopay_payment_method_id: str | None = None

    # Dates
    origination_date: date = field(default_factory=date.today)
    maturity_date: date | None = None
    last_payment_date: date | None = None

    # Status
    is_active: bool = True

    def payoff_amount(self, as_of_date: date | None = None) -> Decimal:
        """Calculate payoff amount including accrued interest.

        Returns the amount needed to pay off the loan in full.
        """
        target_date = as_of_date or date.today()

        # Calculate days of accrued interest since last payment
        last_date = self.last_payment_date or self.origination_date
        days = (target_date - last_date).days

        # Daily interest = balance * (annual_rate / 100 / 365)
        daily_rate = self.interest_rate / Decimal("100") / Decimal("365")
        accrued_interest = self.current_balance * daily_rate * Decimal(days)

        # Payoff = current balance + accrued interest (escrow not included)
        return (self.current_balance + accrued_interest).quantize(Decimal("0.01"))

    def calculate_monthly_payment(self) -> Decimal:
        """Recalculate the monthly P&I payment based on current balance and rate."""
        if self.remaining_months <= 0:
            return Decimal("0.00")

        monthly_rate = self.interest_rate / Decimal("100") / Decimal("12")
        n = self.remaining_months

        if monthly_rate == 0:
            return (self.current_balance / Decimal(n)).quantize(Decimal("0.01"))

        # Standard amortization: M = P * [r(1+r)^n] / [(1+r)^n - 1]
        factor = (1 + monthly_rate) ** n
        payment = self.current_balance * (monthly_rate * factor) / (factor - 1)
        return payment.quantize(Decimal("0.01"))


@dataclass
class PaymentPlan:
    """Repayment plan for past-due amounts."""

    id: str
    loan_id: str
    start_date: date
    end_date: date
    total_past_due: Decimal
    additional_monthly_amount: Decimal  # Extra amount per month
    payments_remaining: int
    status: str = "active"  # active, completed, failed
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class ForbearanceRequest:
    """Forbearance or hardship request."""

    id: str
    loan_id: str
    customer_id: str
    request_date: date
    reason: str  # job_loss, medical, disaster, etc.
    requested_months: int  # Months of forbearance requested
    status: LossMitigationStatus = LossMitigationStatus.REQUESTED
    approved_months: int | None = None
    start_date: date | None = None
    end_date: date | None = None
    notes: str = ""
    created_at: datetime = field(default_factory=datetime.now)


# Type hints for collections of records
PaymentMethods = dict[str, PaymentMethod]  # keyed by method_id
PaymentSchedules = list[PaymentSchedule]
PaymentHistoryList = list[PaymentHistory]
