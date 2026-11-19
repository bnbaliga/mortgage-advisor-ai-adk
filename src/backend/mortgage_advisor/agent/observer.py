"""Observer agent — analyzes tool results and injects suggestions.

The observer runs in the after_tool_callback (audit) and:
1. Analyzes verification results for credit activity signals
2. Detects payment patterns (suggest autopay for manual payers)
3. Flags delinquency risk signals
4. Injects suggestions into CallState for the persona to use

Suggestions are natural language hints that the persona incorporates
into conversation naturally, not robotic script insertions.
"""
from __future__ import annotations

import logging
from typing import Optional

from mortgage_advisor.services.origination import CallState

log = logging.getLogger("mortgage_advisor.agent.observer")


def analyze_tool_result(tool_name: str, result: dict, call: CallState) -> list[str]:
    """Analyze a tool result and generate suggestions.

    Args:
        tool_name: Name of the tool that just ran
        result: The tool's response dict
        call: Current call state

    Returns:
        List of suggestion strings to inject into persona
    """
    suggestions = []

    # Only analyze successful results
    if result.get("result") != "ok":
        return suggestions

    # Route to specific analyzers
    if tool_name == "verify_customer":
        suggestions.extend(_analyze_verification(result, call))
    elif tool_name == "get_loan_balance":
        suggestions.extend(_analyze_balance(result, call))
    elif tool_name == "get_payment_history":
        suggestions.extend(_analyze_payment_history(result, call))
    elif tool_name == "change_payment_date":
        suggestions.extend(_analyze_date_change(result, call))

    return suggestions


def _analyze_verification(result: dict, call: CallState) -> list[str]:
    """Analyze verification results for opportunities."""
    suggestions = []

    # Check if they have multiple properties
    properties = result.get("properties", [])
    if len(properties) > 1:
        # Look for equity opportunities
        high_equity = [p for p in properties if p.get("type") == "primary"]
        if high_equity:
            suggestions.append(
                "Customer has multiple properties - if discussing equity access, "
                "mention they could use their primary residence for a HELOC"
            )

    return suggestions


def _analyze_balance(result: dict, call: CallState) -> list[str]:
    """Analyze balance inquiry for payment suggestions."""
    suggestions = []

    # Check delinquency
    dpd = result.get("days_past_due", 0)
    if dpd > 0:
        amount = result.get("amount_past_due", "")
        if dpd < 30:
            suggestions.append(
                f"Account is {dpd} days past due ({amount}). "
                "Gently offer to take a payment now to get current."
            )
        elif dpd < 60:
            suggestions.append(
                f"Account is {dpd} days past due. Express empathy and ask "
                "if they're experiencing any hardship - mention payment options."
            )
        else:
            suggestions.append(
                f"Account is significantly past due. Be empathetic and mention "
                "hardship and forbearance options may be available."
            )
            call.risk_flags.append("severe_delinquency")

    # Check if autopay is not enabled
    if not result.get("autopay_enabled", False):
        suggestions.append(
            "Autopay is not set up. If they're making manual payments, "
            "casually mention autopay could save them time."
        )

    return suggestions


def _analyze_payment_history(result: dict, call: CallState) -> list[str]:
    """Analyze payment history for patterns."""
    suggestions = []

    payments = result.get("payments", [])
    if not payments:
        return suggestions

    # Count consecutive manual payments
    consecutive_manual = 0
    for payment in payments:
        # All payments in history are "completed" - they made them manually if not on autopay
        consecutive_manual += 1

    # If 6+ consecutive manual payments, suggest autopay
    if consecutive_manual >= 6:
        suggestions.append(
            "Customer has made 6+ consecutive manual payments. "
            "They might appreciate autopay for convenience."
        )

    # Check for any late payments in history
    late_payments = [p for p in payments if p.get("status") == "late"]
    if late_payments:
        call.risk_flags.append("payment_history_late")

    return suggestions


def _analyze_date_change(result: dict, call: CallState) -> list[str]:
    """Analyze payment date change for risk signals."""
    suggestions = []

    # Date change might indicate cash flow concerns
    suggestions.append(
        "Since they changed their due date, gently ask if they'd like "
        "to schedule their next payment now to make sure it's covered."
    )

    return suggestions


def get_proactive_suggestions(call: CallState) -> list[str]:
    """Get proactive suggestions based on overall call state.

    Called at key moments to inject helpful talking points.
    """
    suggestions = []

    # Check risk flags accumulated during the call
    if "severe_delinquency" in call.risk_flags:
        suggestions.append(
            "Before ending, make sure they know about hardship options "
            "and how to reach the loss mitigation team."
        )

    if "payment_history_late" in call.risk_flags:
        if not call.observer_suggestions:  # Don't repeat
            suggestions.append(
                "There have been some late payments - autopay could help "
                "avoid late fees in the future."
            )

    return suggestions


def clear_suggestions(call: CallState) -> None:
    """Clear observer suggestions after they've been used."""
    call.observer_suggestions.clear()
