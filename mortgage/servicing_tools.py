"""Ivy's abilities — ADK function tools for loan servicing.

Tools for the servicing phase of the loan lifecycle:
- Balance inquiries and payoff quotes
- Payment history and schedules
- Autopay setup and management
- Payment date changes
- Secure card capture (mock DTMF)
- One-time payments with authorization

These tools require different verification levels:
- BASIC: get_loan_balance, get_payment_history
- STRONG: change_payment_date, setup_autopay, make_payment
"""
from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Optional

from google.adk.tools.tool_context import ToolContext

from mortgage.database import get_servicing_db
from mortgage.mortgage import CallState, IdentityStrength, MortgageStore, format_currency
from mortgage.servicing import (
    PaymentHistory,
    PaymentMethod,
    PaymentMethodType,
    PaymentSchedule,
    PaymentStatus,
)

# Import tools module to access store dynamically (not at module load time)
from mortgage import tools


def _get_call(tool_context: ToolContext) -> CallState:
    """Get the current call state."""
    return tools.store.call(tool_context.session.id)


def _err(code: str, message: str, say: str = "") -> dict:
    """Return an error response."""
    return {"result": "error", "code": code, "message": message, "say": say}


def _new_ref() -> str:
    """Generate a confirmation reference number."""
    return f"REF{datetime.now().strftime('%Y%m%d%H%M%S')}{uuid.uuid4().hex[:4].upper()}"


# ------------------------------------------------------------- Balance & Info ---

async def get_loan_balance(tool_context: ToolContext) -> dict:
    """Get the current loan balance and next payment due.

    Returns the principal balance, next payment amount and date, and escrow balance.
    Requires basic verification (name + phone last 4).
    """
    call = _get_call(tool_context)

    if not call.verified_customer_id:
        return _err("not_verified", "Customer not verified",
                    "Ask for their name and the last 4 digits of their phone number to pull up their account.")

    db = get_servicing_db()
    loan = db.get_loan_by_customer(call.verified_customer_id)

    if not loan:
        return _err("no_loan", "No active loan found",
                    "Let them know you couldn't find an active loan and offer to connect with a loan officer.")

    # Store the verified loan ID for other tools
    call.verified_loan_id = loan.id

    # Get next scheduled payment
    next_payment = db.get_next_payment(loan.id)

    # Check delinquency
    delinquency = db.get_delinquency_status(loan.id)

    result = {
        "result": "ok",
        "customer_name": loan.customer_name,
        "property_address": loan.property_address,
        "current_balance": format_currency(float(loan.current_balance)),
        "interest_rate": f"{loan.interest_rate}%",
        "monthly_payment": format_currency(float(loan.monthly_payment)),
        "payment_day": loan.payment_day,
        "escrow_balance": format_currency(float(loan.escrow_balance)),
        "autopay_enabled": loan.autopay_enabled,
    }

    if next_payment:
        result["next_due_date"] = next_payment.due_date.strftime("%B %d, %Y")
        result["next_payment_amount"] = format_currency(float(next_payment.total_amount))

    # Add delinquency info if applicable
    if delinquency.days_past_due > 0:
        result["days_past_due"] = delinquency.days_past_due
        result["amount_past_due"] = format_currency(float(delinquency.amount_past_due))
        result["delinquency_stage"] = delinquency.stage.value
        result["say"] = ("Let them know they have a past due balance. Be empathetic and offer to "
                        "discuss payment options or set up a payment today.")
    else:
        result["say"] = "Share the balance and next payment info. If they make manual payments, suggest autopay for convenience."

    return result


async def get_payment_history(limit: int = 6, tool_context: ToolContext = None) -> dict:
    """Get recent payment history for the loan.

    Args:
        limit: Number of recent payments to return (default 6, max 12).

    Requires basic verification.
    """
    call = _get_call(tool_context)

    if not call.verified_customer_id:
        return _err("not_verified", "Customer not verified",
                    "Ask for their name and the last 4 digits of their phone number first.")

    db = get_servicing_db()
    loan = db.get_loan_by_customer(call.verified_customer_id)

    if not loan:
        return _err("no_loan", "No active loan found", "")

    limit = min(max(1, limit), 12)
    payments = db.get_payment_history(loan.id, limit)

    if not payments:
        return {
            "result": "ok",
            "payments": [],
            "say": "Let them know you don't see any recent payments on record."
        }

    payment_list = []
    for p in payments:
        payment_list.append({
            "date": p.payment_date.strftime("%B %d, %Y"),
            "amount": format_currency(float(p.amount)),
            "method": f"...{p.payment_method_last_four}",
            "status": p.status.value,
            "confirmation": p.confirmation_number
        })

    return {
        "result": "ok",
        "payments": payment_list,
        "total_shown": len(payment_list),
        "say": "Share the recent payment history. Note any missed or late payments if present."
    }


async def get_payoff_quote(good_through_days: int = 10, tool_context: ToolContext = None) -> dict:
    """Get a payoff quote for the loan.

    Args:
        good_through_days: Number of days the quote is valid (default 10, max 30).

    Requires basic verification.
    """
    call = _get_call(tool_context)

    if not call.verified_customer_id:
        return _err("not_verified", "Customer not verified", "")

    db = get_servicing_db()
    loan = db.get_loan_by_customer(call.verified_customer_id)

    if not loan:
        return _err("no_loan", "No active loan found", "")

    good_through_days = min(max(1, good_through_days), 30)
    good_through_date = date.today() + timedelta(days=good_through_days)

    payoff_amount = loan.payoff_amount(good_through_date)

    return {
        "result": "ok",
        "payoff_amount": format_currency(float(payoff_amount)),
        "good_through_date": good_through_date.strftime("%B %d, %Y"),
        "current_balance": format_currency(float(loan.current_balance)),
        "daily_interest": format_currency(float(loan.current_balance * loan.interest_rate / Decimal("36500"))),
        "note": "This is an estimated payoff. For an official payoff statement, contact our payoff department.",
        "say": "Give them the payoff amount and the good-through date. Mention it's an estimate and daily interest accrues."
    }


# ------------------------------------------------------------- Payment Date Changes ---

async def change_payment_date(new_payment_day: int, tool_context: ToolContext = None) -> dict:
    """Change the monthly payment due date.

    Args:
        new_payment_day: The new day of month for payments (1-28).

    Requires strong verification. This change takes effect next billing cycle.
    """
    call = _get_call(tool_context)

    if not call.is_verified_strong:
        return _err("need_strong_verification", "Strong verification required",
                    "For security, ask them to confirm their date of birth and approximate loan balance.")

    if not (1 <= new_payment_day <= 28):
        return _err("invalid_day", "Payment day must be between 1 and 28",
                    "Ask them which day between the 1st and 28th they'd like their payment due.")

    db = get_servicing_db()
    loan = db.get_loan_by_customer(call.verified_customer_id)

    if not loan:
        return _err("no_loan", "No active loan found", "")

    old_day = loan.payment_day

    # Update the loan
    loan.payment_day = new_payment_day

    # Calculate new next due date
    today = date.today()
    if today.day >= new_payment_day:
        # Next month
        if today.month == 12:
            new_due = date(today.year + 1, 1, new_payment_day)
        else:
            new_due = date(today.year, today.month + 1, new_payment_day)
    else:
        new_due = date(today.year, today.month, new_payment_day)

    loan.next_due_date = new_due
    db.update_loan(loan)

    return {
        "result": "ok",
        "previous_day": old_day,
        "new_day": new_payment_day,
        "next_due_date": new_due.strftime("%B %d, %Y"),
        "next_payment": format_currency(float(loan.monthly_payment)),
        "say": f"Confirm the due date has been changed from the {old_day}th to the {new_payment_day}th. "
               f"Their next payment of {format_currency(float(loan.monthly_payment))} is due {new_due.strftime('%B %d')}."
    }


# ------------------------------------------------------------- Autopay Management ---

async def get_autopay_status(tool_context: ToolContext = None) -> dict:
    """Check if autopay is enabled and which payment method is used.

    Requires basic verification.
    """
    call = _get_call(tool_context)

    if not call.verified_customer_id:
        return _err("not_verified", "Customer not verified", "")

    db = get_servicing_db()
    loan = db.get_loan_by_customer(call.verified_customer_id)

    if not loan:
        return _err("no_loan", "No active loan found", "")

    if not loan.autopay_enabled:
        return {
            "result": "ok",
            "autopay_enabled": False,
            "say": "Let them know autopay is not currently set up. Offer to enable it for them."
        }

    # Get the autopay payment method
    method = None
    if loan.autopay_payment_method_id:
        method = db.get_payment_method(loan.autopay_payment_method_id)

    result = {
        "result": "ok",
        "autopay_enabled": True,
        "payment_day": loan.payment_day,
        "amount": format_currency(float(loan.monthly_payment)),
    }

    if method:
        result["payment_method"] = method.display_name()
        result["payment_method_last_four"] = method.last_four

    result["say"] = "Let them know autopay is active and share the payment method details."
    return result


async def setup_autopay(payment_method_id: str = "", tool_context: ToolContext = None) -> dict:
    """Enable autopay using a payment method on file.

    Args:
        payment_method_id: ID of the payment method to use. If empty, uses the default.

    Requires strong verification.
    """
    call = _get_call(tool_context)

    if not call.is_verified_strong:
        return _err("need_strong_verification", "Strong verification required",
                    "For security, ask them to confirm their date of birth and approximate loan balance.")

    db = get_servicing_db()
    loan = db.get_loan_by_customer(call.verified_customer_id)

    if not loan:
        return _err("no_loan", "No active loan found", "")

    # Get payment method
    if payment_method_id:
        method = db.get_payment_method(payment_method_id)
    else:
        method = db.get_default_payment_method(call.verified_customer_id)

    if not method:
        return _err("no_payment_method", "No payment method found",
                    "Ask them to add a payment method first, or check if they have a card or bank account to set up.")

    # Enable autopay
    loan.autopay_enabled = True
    loan.autopay_payment_method_id = method.id
    db.update_loan(loan)

    # Mark the method as autopay
    method.is_autopay = True
    db.update_payment_method(method)

    return {
        "result": "ok",
        "autopay_enabled": True,
        "payment_method": method.display_name(),
        "payment_day": loan.payment_day,
        "amount": format_currency(float(loan.monthly_payment)),
        "say": f"Confirm autopay is now set up. Payments of {format_currency(float(loan.monthly_payment))} "
               f"will be automatically drafted on the {loan.payment_day}th of each month from {method.display_name()}."
    }


async def cancel_autopay(tool_context: ToolContext = None) -> dict:
    """Cancel automatic payments.

    Requires strong verification.
    """
    call = _get_call(tool_context)

    if not call.is_verified_strong:
        return _err("need_strong_verification", "Strong verification required",
                    "For security, ask them to confirm their date of birth and approximate loan balance.")

    db = get_servicing_db()
    loan = db.get_loan_by_customer(call.verified_customer_id)

    if not loan:
        return _err("no_loan", "No active loan found", "")

    if not loan.autopay_enabled:
        return {
            "result": "ok",
            "message": "Autopay was not enabled",
            "say": "Let them know autopay was already off."
        }

    # Clear autopay on the method if set
    if loan.autopay_payment_method_id:
        method = db.get_payment_method(loan.autopay_payment_method_id)
        if method:
            method.is_autopay = False
            db.update_payment_method(method)

    # Disable autopay on loan
    loan.autopay_enabled = False
    loan.autopay_payment_method_id = None
    db.update_loan(loan)

    return {
        "result": "ok",
        "autopay_enabled": False,
        "next_due_date": loan.next_due_date.strftime("%B %d, %Y"),
        "say": f"Confirm autopay has been cancelled. Remind them their next payment of "
               f"{format_currency(float(loan.monthly_payment))} is due {loan.next_due_date.strftime('%B %d')} "
               f"and they'll need to make it manually."
    }


# ------------------------------------------------------------- Payment Methods ---

async def get_payment_methods(tool_context: ToolContext = None) -> dict:
    """Get all payment methods on file for the customer.

    Requires basic verification.
    """
    call = _get_call(tool_context)

    if not call.verified_customer_id:
        return _err("not_verified", "Customer not verified", "")

    db = get_servicing_db()
    methods = db.get_payment_methods_by_customer(call.verified_customer_id)

    if not methods:
        return {
            "result": "ok",
            "methods": [],
            "say": "Let them know there are no payment methods on file. Offer to add one."
        }

    method_list = []
    for m in methods:
        method_list.append({
            "id": m.id,
            "type": m.method_type.value,
            "display": m.display_name(),
            "last_four": m.last_four,
            "is_default": m.is_default,
            "is_autopay": m.is_autopay
        })

    return {
        "result": "ok",
        "methods": method_list,
        "say": "Read back the payment methods on file. Note which is default and which is used for autopay."
    }


async def initiate_secure_card_capture(card_type: str = "debit", tool_context: ToolContext = None) -> dict:
    """Initiate secure DTMF keypad capture for card number entry.

    Args:
        card_type: Type of card - "debit" or "credit".

    This triggers the telephony layer to capture card digits via keypad.
    The agent should instruct the caller to enter their card number on the phone keypad.
    Card numbers are NEVER transcribed from voice for security.

    Requires strong verification.
    """
    call = _get_call(tool_context)

    if not call.is_verified_strong:
        return _err("need_strong_verification", "Strong verification required",
                    "For security, ask them to confirm their date of birth and approximate loan balance first.")

    # Set up secure capture state
    call.secure_capture_pending = True
    call.secure_capture_type = "card"

    # In a real system, this would trigger DTMF capture via telephony
    # For the mock, we'll simulate a successful capture with a test token

    return {
        "result": "ok",
        "capture_initiated": True,
        "capture_type": "card",
        "instructions": [
            "Please enter your 16-digit card number on your phone keypad now.",
            "Then enter the 4-digit expiration as month and year.",
            "Finally, enter the 3-digit security code."
        ],
        "say": "Ask them to enter their 16-digit card number using their phone keypad. "
               "Explain this is for security - you won't hear the numbers."
    }


async def complete_secure_card_capture(
    card_network: str,
    last_four: str,
    expiration: str,
    tool_context: ToolContext = None
) -> dict:
    """Complete the secure card capture with tokenized result.

    This is called by the telephony layer after DTMF capture completes.
    In the mock implementation, we simulate receiving the tokenized result.

    Args:
        card_network: Detected card network (Visa, Mastercard, etc.)
        last_four: Last 4 digits of the card
        expiration: Expiration in MM/YY format

    Requires strong verification and active secure capture session.
    """
    call = _get_call(tool_context)

    if not call.secure_capture_pending:
        return _err("no_capture", "No secure capture in progress",
                    "Start the card capture process first.")

    # Create the payment method
    db = get_servicing_db()

    # Generate a mock token
    token = f"tok_{card_network.lower()}_{last_four}_{uuid.uuid4().hex[:8]}"

    method = PaymentMethod(
        id="",  # Will be generated
        customer_id=call.verified_customer_id,
        method_type=PaymentMethodType.DEBIT_CARD,
        last_four=last_four,
        institution_name=card_network,
        nickname=None,
        is_default=False,
        is_autopay=False,
        token=token,
        expiration_date=expiration,
        created_at=datetime.now()
    )

    method = db.add_payment_method(method)
    call.clear_secure_capture()

    return {
        "result": "ok",
        "payment_method_id": method.id,
        "card_network": card_network,
        "last_four": last_four,
        "expiration": expiration,
        "say": f"Confirm you've captured the {card_network} card ending in {last_four}. "
               "Ask if they'd like to use this card to make a payment or set up autopay."
    }


async def add_bank_account(
    account_type: str,
    routing_number: str,
    account_last_four: str,
    bank_name: str,
    nickname: str = "",
    tool_context: ToolContext = None
) -> dict:
    """Add a bank account as a payment method.

    Args:
        account_type: "checking" or "savings"
        routing_number: 9-digit ABA routing number
        account_last_four: Last 4 digits of account number
        bank_name: Name of the bank
        nickname: Optional nickname for the account

    Note: Full account number would be captured via secure channel in production.
    Requires strong verification.
    """
    call = _get_call(tool_context)

    if not call.is_verified_strong:
        return _err("need_strong_verification", "Strong verification required", "")

    # Validate routing number format
    if len(routing_number) != 9 or not routing_number.isdigit():
        return _err("invalid_routing", "Routing number must be 9 digits",
                    "Ask them for the 9-digit routing number from their check or bank statement.")

    db = get_servicing_db()

    method_type = PaymentMethodType.CHECKING if account_type.lower() == "checking" else PaymentMethodType.SAVINGS

    # Generate a mock token
    token = f"tok_ach_{routing_number[-4:]}_{account_last_four}_{uuid.uuid4().hex[:8]}"

    method = PaymentMethod(
        id="",
        customer_id=call.verified_customer_id,
        method_type=method_type,
        last_four=account_last_four,
        institution_name=bank_name,
        nickname=nickname or None,
        is_default=False,
        is_autopay=False,
        token=token,
        expiration_date=None,
        created_at=datetime.now()
    )

    method = db.add_payment_method(method)

    return {
        "result": "ok",
        "payment_method_id": method.id,
        "bank_name": bank_name,
        "account_type": account_type,
        "last_four": account_last_four,
        "say": f"Confirm the {bank_name} {account_type} account ending in {account_last_four} has been added. "
               "Ask if they'd like to use this account to make a payment or set up autopay."
    }


async def set_default_payment_method(payment_method_id: str, tool_context: ToolContext = None) -> dict:
    """Set a payment method as the default.

    Args:
        payment_method_id: ID of the payment method to set as default.

    Requires strong verification.
    """
    call = _get_call(tool_context)

    if not call.is_verified_strong:
        return _err("need_strong_verification", "Strong verification required", "")

    db = get_servicing_db()
    method = db.get_payment_method(payment_method_id)

    if not method or method.customer_id != call.verified_customer_id:
        return _err("not_found", "Payment method not found", "")

    db.set_default_payment_method(call.verified_customer_id, payment_method_id)

    return {
        "result": "ok",
        "default_method": method.display_name(),
        "say": f"Confirm the {method.display_name()} is now the default payment method."
    }


async def remove_payment_method(payment_method_id: str, tool_context: ToolContext = None) -> dict:
    """Remove a payment method from the account.

    Args:
        payment_method_id: ID of the payment method to remove.

    Cannot remove a method that is currently set for autopay.
    Requires strong verification.
    """
    call = _get_call(tool_context)

    if not call.is_verified_strong:
        return _err("need_strong_verification", "Strong verification required", "")

    db = get_servicing_db()
    method = db.get_payment_method(payment_method_id)

    if not method or method.customer_id != call.verified_customer_id:
        return _err("not_found", "Payment method not found", "")

    if method.is_autopay:
        return _err("autopay_active", "Cannot remove autopay payment method",
                    "Let them know they need to cancel autopay or change to a different method first.")

    display_name = method.display_name()
    db.delete_payment_method(payment_method_id)

    return {
        "result": "ok",
        "removed": display_name,
        "say": f"Confirm the {display_name} has been removed from their account."
    }


# ------------------------------------------------------------- Make Payment ---

async def prepare_payment(
    amount: float,
    payment_date: str = "",
    payment_method_id: str = "",
    tool_context: ToolContext = None
) -> dict:
    """Prepare a one-time payment for authorization.

    Args:
        amount: Payment amount in dollars.
        payment_date: Date to process payment (YYYY-MM-DD). Empty for today.
        payment_method_id: Payment method to use. Empty for default.

    This sets up the payment details and requires explicit authorization before processing.
    Requires strong verification.
    """
    call = _get_call(tool_context)

    if not call.is_verified_strong:
        return _err("need_strong_verification", "Strong verification required",
                    "For security, ask them to confirm their date of birth and approximate loan balance.")

    db = get_servicing_db()
    loan = db.get_loan_by_customer(call.verified_customer_id)

    if not loan:
        return _err("no_loan", "No active loan found", "")

    # Validate amount
    if amount <= 0:
        return _err("invalid_amount", "Payment amount must be positive",
                    "Ask them for the payment amount.")

    # Get payment method
    if payment_method_id:
        method = db.get_payment_method(payment_method_id)
    else:
        method = db.get_default_payment_method(call.verified_customer_id)

    if not method:
        return _err("no_payment_method", "No payment method found",
                    "Ask them to add a payment method first.")

    # Parse payment date
    if payment_date:
        try:
            pay_date = date.fromisoformat(payment_date)
        except ValueError:
            return _err("invalid_date", "Invalid date format",
                        "Ask for the date in month, day, year format.")
    else:
        pay_date = date.today()

    # Store pending authorization
    call.pending_authorization = {
        "amount": amount,
        "payment_date": pay_date.isoformat(),
        "payment_method_id": method.id,
        "payment_method_display": method.display_name(),
        "payment_method_last_four": method.last_four,
        "loan_id": loan.id
    }
    call.authorization_confirmed = False

    return {
        "result": "ok",
        "status": "pending_authorization",
        "amount": format_currency(amount),
        "payment_date": pay_date.strftime("%B %d, %Y"),
        "payment_method": method.display_name(),
        "payment_method_last_four": method.last_four,
        "say": f"Read back: 'To confirm: I'll charge {format_currency(amount)} to the account ending in "
               f"{method.last_four} on {pay_date.strftime('%B %d, %Y')}. Do I have your authorization to proceed?'"
    }


async def confirm_payment(authorized: bool = False, tool_context: ToolContext = None) -> dict:
    """Confirm and process a prepared payment.

    Args:
        authorized: Must be True - set only when caller explicitly authorizes.

    Call prepare_payment first, then confirm_payment with authorized=True
    ONLY after the caller explicitly says "yes" to the authorization question.
    """
    call = _get_call(tool_context)

    if not call.pending_authorization:
        return _err("no_payment_pending", "No payment prepared",
                    "Call prepare_payment first to set up the payment details.")

    if not authorized:
        # Clear the pending authorization
        auth = call.pending_authorization
        call.clear_authorization()
        return {
            "result": "cancelled",
            "amount": format_currency(auth["amount"]),
            "say": "Let them know the payment was cancelled. Ask if they'd like to try again or do something else."
        }

    # Process the payment
    db = get_servicing_db()
    auth = call.pending_authorization

    loan = db.get_loan(auth["loan_id"])
    if not loan:
        call.clear_authorization()
        return _err("no_loan", "Loan not found", "")

    # Create payment record
    amount = Decimal(str(auth["amount"]))
    pay_date = date.fromisoformat(auth["payment_date"])

    # Simple split for demo (in reality, this would be calculated properly)
    interest_portion = min(amount, loan.current_balance * loan.interest_rate / Decimal("1200"))
    principal_portion = amount - interest_portion

    payment = PaymentHistory(
        id="",
        loan_id=loan.id,
        payment_date=pay_date,
        amount=amount,
        principal_applied=principal_portion,
        interest_applied=interest_portion,
        escrow_applied=Decimal("0.00"),
        payment_method_id=auth["payment_method_id"],
        payment_method_last_four=auth["payment_method_last_four"],
        status=PaymentStatus.COMPLETED if pay_date == date.today() else PaymentStatus.SCHEDULED,
        confirmation_number=""
    )

    payment = db.add_payment(payment)

    # Update loan balance if payment is for today
    if pay_date == date.today():
        loan.current_balance -= principal_portion
        loan.last_payment_date = pay_date
        db.update_loan(loan)

    call.clear_authorization()

    return {
        "result": "ok",
        "status": "completed" if pay_date == date.today() else "scheduled",
        "confirmation_number": payment.confirmation_number,
        "amount": format_currency(float(amount)),
        "payment_date": pay_date.strftime("%B %d, %Y"),
        "new_balance": format_currency(float(loan.current_balance)),
        "say": f"Confirm the payment: 'Your payment of {format_currency(float(amount))} has been "
               f"{'processed' if pay_date == date.today() else 'scheduled'}. "
               f"Your confirmation number is {payment.confirmation_number}. "
               f"Is there anything else I can help with?'"
    }


# ------------------------------------------------------------- All Servicing Tools ---

SERVICING_TOOLS = [
    # Balance & Info
    get_loan_balance,
    get_payment_history,
    get_payoff_quote,

    # Payment Date
    change_payment_date,

    # Autopay
    get_autopay_status,
    setup_autopay,
    cancel_autopay,

    # Payment Methods
    get_payment_methods,
    initiate_secure_card_capture,
    complete_secure_card_capture,
    add_bank_account,
    set_default_payment_method,
    remove_payment_method,

    # Payments
    prepare_payment,
    confirm_payment,
]
