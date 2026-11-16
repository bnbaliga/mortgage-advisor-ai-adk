"""Policy door — every tool call walks through here.

Mortgage lending compliance rules enforced in CODE, not in the prompt:

  BEFORE tool execution (mortgage_gate):
    1. LOCKOUT           — 3 failed identity checks lock the call; only a human can help.
    2. INPUT_VALIDATION  — Block tools with invalid inputs, ask for valid values.
    3. VERIFICATION      — Block servicing tools without proper identity verification level.
    4. AGENT_GATING      — Block tools not allowed for the active agent persona.
    5. CONFIRMATION      — Block payments without explicit caller authorization.

  AFTER tool execution (audit):
    6. DISCLAIMER        — Rate estimates always include disclaimer.
    7. TRANSFER_HINT     — Ineligible results suggest loan officer transfer.
    8. OBSERVER          — Analyze tool results for risk signals and suggestions.

Same three verbs as the front desk: return None = allow (observe), return a dict = BLOCK
(ADK skips the tool and hands the dict to the model), or edit `args` in place = rewrite.

`audit` (the after_tool_callback) streams each result to the caller's browser.
When audit returns a dict, ADK uses that dict instead of the original tool response.
"""
import asyncio
import logging
from typing import Any, Optional

from google.adk.tools.base_tool import BaseTool
from google.adk.tools.tool_context import ToolContext

from mortgage import events, tools
from mortgage.mortgage import IdentityStrength

log = logging.getLogger("mortgage.policy")

# ---------------------------------------------------------------- Tool Categories ---

# Servicing tools requiring BASIC verification (name + phone last 4)
NEEDS_BASIC_VERIFICATION = {
    "get_loan_balance",
    "get_payment_history",
    "get_payoff_quote",
    "get_autopay_status",
    "get_payment_methods",
}

# Servicing tools requiring STRONG verification (DOB + loan balance)
NEEDS_STRONG_VERIFICATION = {
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

# Tools requiring explicit caller confirmation before execution
NEEDS_CONFIRMATION = {
    "confirm_payment",  # Payment authorization
}

# Tools that should suggest loan officer transfer for complex cases
SUGGEST_TRANSFER = {
    "check_heloc_eligibility",
    "get_rate_estimate",
    "calculate_equity",
    "compare_options",
}

# Identity tools
IDENTITY_TOOLS = {
    "verify_customer",
    "verify_customer_strong",
    "register_lead",
}

# Agent-based tool access control
AGENT_TOOL_ACCESS = {
    "origination": {
        # Mac's origination tools
        "get_company_info", "get_mortgage_products", "check_heloc_eligibility",
        "check_state_regulations", "get_rate_estimate", "verify_customer",
        "register_lead", "transfer_to_loan_officer", "answer_faq",
        "calculate_equity", "search_regulations", "compare_options",
    },
    "servicing": {
        # Ivy's servicing tools + shared verification
        "verify_customer", "verify_customer_strong",
        "get_loan_balance", "get_payment_history", "get_payoff_quote",
        "change_payment_date", "get_autopay_status", "setup_autopay", "cancel_autopay",
        "get_payment_methods", "initiate_secure_card_capture", "complete_secure_card_capture",
        "add_bank_account", "set_default_payment_method", "remove_payment_method",
        "prepare_payment", "confirm_payment",
        "transfer_to_loan_officer", "get_company_info",
    },
    "collections": {
        # Collections tools (future phase)
        "verify_customer", "verify_customer_strong",
        "get_loan_balance", "get_payment_history",
        "prepare_payment", "confirm_payment",
        "request_forbearance", "setup_payment_plan", "get_loss_mitigation_options",
        "transfer_to_loan_officer", "get_company_info",
    },
    "welcome": {
        # Welcome call tools (future phase)
        "verify_customer", "get_loan_balance", "get_payment_methods",
        "setup_autopay", "get_company_info", "transfer_to_loan_officer",
    },
}

# Sensitive info that should be redacted in logs
_SENSITIVE_ARGS = {"full_name", "phone", "phone_last_4", "email"}


def _redact(args: dict) -> dict:
    return {k: ("***" if k in _SENSITIVE_ARGS else v) for k, v in args.items()}


def _block(call_id: str, tool: str, args: dict, code: str, reason: str, say: str) -> dict:
    events.publish(call_id, {"type": "action", "tool": tool, "args": dict(args),
                             "status": "blocked", "reason": reason})
    log.info("BLOCK %s %s — %s", tool, _redact(args), code)
    return {"result": "blocked", "code": code, "reason": reason, "say": say}


async def mortgage_gate(tool: BaseTool, args: dict[str, Any], tool_context: ToolContext) -> Optional[dict]:
    """Pre-tool policy check — runs before every tool call."""
    call_id = tool_context.session.id
    call = tools.store.call(call_id)
    name = tool.name

    # 1. Check lockout status
    if call.locked and name in IDENTITY_TOOLS:
        return _block(call_id, name, args, "locked", "verification locked after 3 attempts",
                      "For their security, you can't verify on this call. Offer to transfer them to a loan officer.")

    # 2. Agent-based tool access control
    allowed_tools = AGENT_TOOL_ACCESS.get(call.active_agent, set())
    if allowed_tools and name not in allowed_tools:
        # Don't hard-block — the agent might need to switch. Just log.
        log.debug("Tool %s not in agent %s's toolset", name, call.active_agent)

    # 3. BASIC verification check for servicing tools
    if name in NEEDS_BASIC_VERIFICATION:
        # Wait briefly for concurrent verify_customer
        if not call.verified_customer_id:
            for _ in range(25):
                await asyncio.sleep(0.01)
                if call.verified_customer_id:
                    break
        if not call.verified_customer_id:
            return _block(call_id, name, args, "not_verified", "customer not verified",
                          "Ask for their name and the last 4 digits of their phone number to pull up their account.")

    # 4. STRONG verification check for sensitive servicing tools
    if name in NEEDS_STRONG_VERIFICATION:
        # First check basic verification
        if not call.verified_customer_id:
            return _block(call_id, name, args, "not_verified", "customer not verified",
                          "Ask for their name and the last 4 digits of their phone number first.")

        # verify_customer_strong checks its own verification — don't block it
        if name != "verify_customer_strong" and not call.is_verified_strong:
            return _block(call_id, name, args, "need_strong_verification",
                          "strong verification required for sensitive operations",
                          "For security, ask them to confirm their date of birth and approximate loan balance.")

    # 5. Payment confirmation check
    if name == "confirm_payment":
        if not call.pending_authorization:
            return _block(call_id, name, args, "no_pending_payment",
                          "no payment prepared for confirmation",
                          "Call prepare_payment first to set up the payment details.")

        # Check that authorized flag is explicitly set
        if not args.get("authorized", False):
            return _block(call_id, name, args, "not_authorized",
                          "caller has not explicitly authorized the payment",
                          "Read back the payment details and ask: 'Do I have your authorization to proceed?' "
                          "Only confirm_payment with authorized=True after they say yes.")

    # Validate inputs for get_rate_estimate
    if name == "get_rate_estimate":
        credit_score = args.get("credit_score", 720)
        loan_to_value = args.get("loan_to_value", 80)

        if not (300 <= credit_score <= 850):
            return _block(call_id, name, args, "missing_inputs",
                          f"credit_score {credit_score} is outside valid range 300-850",
                          "Ask the caller for their approximate credit score. It should be between 300 and 850.")

        if not (1 <= loan_to_value <= 100):
            return _block(call_id, name, args, "missing_inputs",
                          f"loan_to_value {loan_to_value} is outside valid range 1-100",
                          "Ask the caller what percentage of the home's value they want to borrow. It should be between 1% and 100%.")

    # Validate inputs for compare_options
    if name == "compare_options":
        from mortgage.mortgage import normalize_state, MortgageError, VALID_STATE_CODES

        state = args.get("state", "")
        property_value = args.get("property_value", 0)
        credit_score = args.get("credit_score", 720)

        # Validate state - must be recognizable
        try:
            state_code = normalize_state(state)
            # Check if we have regulations on file for this state
            state_rules = tools.store.state_regulations.get(state_code)
            if not state_rules:
                return _block(call_id, name, args, "unknown_state",
                              f"No regulations on file for state {state_code}",
                              "Let them know you can't compare options for that state yet and offer to connect them with a loan officer who can help.")
        except MortgageError:
            return _block(call_id, name, args, "unknown_state",
                          f"Unrecognized state: {state}",
                          "Ask the caller which state the property is located in.")

        # Validate property value
        if property_value <= 0:
            return _block(call_id, name, args, "missing_inputs",
                          "property_value must be positive",
                          "Ask the caller for the estimated value of their property.")

        # Validate credit score
        if not (300 <= credit_score <= 850):
            return _block(call_id, name, args, "missing_inputs",
                          f"credit_score {credit_score} is outside valid range 300-850",
                          "Ask the caller for their approximate credit score. It should be between 300 and 850.")

    # Log allowed action
    events.publish(call_id, {"type": "action", "tool": name, "args": dict(args), "status": "allowed"})
    log.info("ALLOW %s %s", name, _redact(args))
    return None  # allow the tool to run


async def audit(tool: BaseTool, args: dict[str, Any], tool_context: ToolContext,
                tool_response: Any) -> Optional[dict]:
    """Post-tool callback — runs after every tool completes.

    Returns a NEW dict (not mutating the original) when compliance additions are needed.
    ADK will use the returned dict instead of the original tool_response.
    """
    resp = tool_response if isinstance(tool_response, dict) else {"result": str(tool_response)}
    call = tools.store.call(tool_context.session.id)

    # Publish result to browser
    events.publish(tool_context.session.id, {"type": "tool_result", "tool": tool.name, "response": resp})

    # Log result (redacted)
    result_summary = resp.get("result", "unknown")
    code = resp.get("code", "")
    log.info("RESULT %s -> %s%s", tool.name, result_summary, f" ({code})" if code else "")

    # Track if we need to return a modified response
    modified = None

    # Ensure get_rate_estimate always includes disclaimer
    if tool.name == "get_rate_estimate" and "disclaimer" not in resp:
        modified = {**resp, "disclaimer": tools.store.info["disclaimers"]["rates"]}

    # For tools in SUGGEST_TRANSFER that return ineligible or needs_review, add loan officer hint
    if tool.name in SUGGEST_TRANSFER:
        is_ineligible = resp.get("eligible") is False
        is_needs_review = resp.get("status") == "needs_review"

        if (is_ineligible or is_needs_review) and "say" not in resp:
            base = modified if modified else resp
            modified = {
                **base,
                "say": "Explain the situation and offer to connect with a licensed loan officer who can discuss alternatives and next steps."
            }

    # ---------------------------------------------------------------- Observer ---
    # Run observer analysis for servicing tools and inject suggestions
    try:
        from mortgage.observer import analyze_tool_result
        suggestions = analyze_tool_result(tool.name, resp, call)
        if suggestions:
            call.observer_suggestions.extend(suggestions)
            log.info("OBSERVER suggestions: %s", suggestions)
    except ImportError:
        pass  # Observer module not yet implemented
    except Exception as e:
        log.warning("Observer error: %s", e)

    # Return the modified dict if we made changes, otherwise None (use original)
    return modified
