"""Mac's abilities — ADK function tools for mortgage advising.

Same pattern as the front desk tools:
  - Plain `async def`s: ADK builds the schema from the signature + docstring
  - Every tool returns INSTANTLY — they only touch the in-memory `MortgageStore`
  - Results are written for the MODEL to paraphrase out loud
  - The tools never expose internal IDs to the caller

Who may call what is decided in `policy.py`, the one door every call walks through.
"""

from google.adk.tools.tool_context import ToolContext

from mortgage.mortgage import (
    IdentityStrength,
    MortgageError,
    MortgageStore,
    format_currency,
    format_rate,
    spoken_time,
)

store = MortgageStore.load()


def use_store(s: MortgageStore) -> None:
    """Swap the backing store (tests, or a real LOS adapter)."""
    global store
    store = s


def _err(e: MortgageError) -> dict:
    return {"result": "error", "code": e.code, "message": e.message}


def _caller(tool_context: ToolContext) -> str | None:
    return store.call(tool_context.session.id).verified_customer_id


# ------------------------------------------------------------- company info ---


async def get_company_info(topic: str) -> dict:
    """Look up company information: hours, contact, products, rates, or general info.

    Args:
        topic: one of hours, contact, products, rates, value_proposition, disclaimers, or "all".
    """
    c = store.info
    # Build hours list from store.hours using the spoken_time helper
    hours = [
        f"{d.title()}: " + (f"{spoken_time(h[0])} to {spoken_time(h[1])}" if h else "closed")
        for d, h in store.hours.items()
    ]

    products_list = [f"{p['name']}: {p['description']}" for p in store.products.values()]

    facts = {
        "hours": hours,
        "contact": {"phone": c["phone"], "website": c.get("website", ""), "address": c["address"]},
        "products": products_list,
        "value_proposition": c.get("value_proposition", ""),
        "nmls": c.get("nmls_id", ""),
        "disclaimers": c.get("disclaimers", {}),
    }

    key = (topic or "all").strip().lower().replace(" ", "_")
    if key in facts:
        return {"result": "ok", key: facts[key]}
    return {"result": "ok", **facts}


async def get_mortgage_products(product_type: str = "") -> dict:
    """Get information about available mortgage products.

    Args:
        product_type: optional specific product like "heloc", "conventional_30", "fha", "va",
            "jumbo", "cash_out_refi". Empty returns all products.
    """
    if product_type:
        key = product_type.lower().replace(" ", "_").replace("-", "_")
        product = store.products.get(key)
        if product:
            return {
                "result": "ok",
                "product": {
                    "name": product["name"],
                    "description": product["description"],
                    "rate_range": f"{format_rate(product['rate_range'][0])} to {format_rate(product['rate_range'][1])}",
                    "min_credit_score": product.get("min_credit_score", "varies"),
                    "max_ltv": product.get("max_ltv", "varies"),
                    "property_types": product.get("property_types", []),
                    "notes": product.get("notes", ""),
                },
            }
        return {
            "result": "error",
            "code": "unknown_product",
            "message": f"I don't have information about '{product_type}'. Our products include: "
            + ", ".join(store.products.keys()),
        }

    # Return summary of all products
    products = []
    for key, p in store.products.items():
        products.append(
            {
                "id": key,
                "name": p["name"],
                "rate_range": f"{format_rate(p['rate_range'][0])} to {format_rate(p['rate_range'][1])}",
            }
        )
    return {"result": "ok", "products": products}


# ------------------------------------------------------------- eligibility checks ---


async def check_heloc_eligibility(
    state: str,
    property_type: str,
    has_existing_cashout: bool = False,
    property_value: float = 0,
    current_mortgage_balance: float = 0,
) -> dict:
    """Check if a HELOC is allowed based on state regulations and property details.

    Args:
        state: two-letter state code (e.g., "TX", "CA") or state name.
        property_type: the caller's own words describing the property use — e.g., "rental",
            "investment property", "my home", "primary residence", "vacation home". The system
            will normalize these to standard categories.
        has_existing_cashout: true if there's an existing cash-out refinance on the property.
        property_value: estimated property value in dollars (optional, for calculating max HELOC amount).
        current_mortgage_balance: current mortgage balance in dollars (optional).
    """
    from mortgage.mortgage import MortgageError

    try:
        result = store.check_heloc_eligibility(
            state, property_type, has_existing_cashout, property_value, current_mortgage_balance
        )
    except MortgageError as e:
        return _err(e)

    # Handle needs_review status (state has no rules on file)
    if result.get("status") == "needs_review":
        return {
            "result": "ok",
            "eligible": None,
            "state": result["state"],
            "status": "needs_review",
            "say": result["say"],
        }

    if result["eligible"]:
        response = {"result": "ok", "eligible": True, "state": result["state"]}
        if "max_heloc_amount" in result:
            response["max_heloc_amount"] = format_currency(result["max_heloc_amount"])
            response["current_ltv"] = f"{result['current_ltv']}%"
        if "note" in result:
            response["note"] = result["note"]
        return response
    else:
        return {
            "result": "ok",
            "eligible": False,
            "state": result["state"],
            "issues": result["issues"],
            "alternatives": result["alternatives"],
            "say": "Explain the restrictions kindly and present the alternatives.",
        }


async def check_state_regulations(state: str, product_type: str = "heloc") -> dict:
    """Look up state-specific lending regulations.

    Args:
        state: two-letter state code (e.g., "TX", "CA") or state name.
        product_type: "heloc" or "cashout" for specific rules.
    """
    from mortgage.mortgage import MortgageError

    try:
        state_code, rules = store.get_state_rules(state, product_type)
    except MortgageError as e:
        return _err(e)

    if not rules:
        return {
            "result": "ok",
            "state": state_code,
            "status": "needs_review",
            "say": "Explain you don't have specific regulations on file for that state and offer to connect them with a licensed loan officer who can provide accurate guidance.",
        }

    return {"result": "ok", "state": state_code, "rules": rules}


async def get_rate_estimate(
    product_type: str, credit_score: int = 720, loan_to_value: float = 80
) -> dict:
    """Get an estimated rate for a mortgage product.

    Args:
        product_type: the product like "conventional_30", "fha", "heloc".
        credit_score: the borrower's credit score (approximate is fine).
        loan_to_value: the loan-to-value ratio as a percentage.
    """
    try:
        estimate = store.get_rate_estimate(product_type, credit_score, loan_to_value)
        result = {
            "result": "ok",
            "product": estimate["product"],
            "estimated_rate": format_rate(estimate["estimated_rate"]),
            "disclaimer": estimate["disclaimer"],
            "say": "Give them the estimated rate and mention this is an estimate that depends on full application review.",
        }
        # Add optional fields if present (rate sheet vs fallback returns different data)
        if "rate_range" in estimate:
            result["range"] = estimate["rate_range"]
        if "credit_tier" in estimate:
            result["credit_tier"] = estimate["credit_tier"]
        if "ltv_band" in estimate:
            result["ltv_band"] = estimate["ltv_band"]
        if "market_benchmark" in estimate:
            result["market_benchmark"] = format_rate(estimate["market_benchmark"])
            result["benchmark_source"] = estimate.get("benchmark_source")
        return result
    except MortgageError as e:
        return _err(e)


# ------------------------------------------------------------- customer verification ---


async def verify_customer(full_name: str, phone_last_4: str, tool_context: ToolContext) -> dict:
    """Verify an existing customer's identity. Use when they say they've worked with us before.

    Args:
        full_name: the customer's first and last name.
        phone_last_4: the last 4 digits of their phone number on file.
    """
    call = store.call(tool_context.session.id)
    customer = store.find_customer(full_name, phone_last_4)

    if not customer:
        call.failed_verifications += 1
        left = max(0, 3 - call.failed_verifications)
        return {
            "result": "error",
            "code": "no_match",
            "attempts_left": left,
            "message": (
                "I couldn't find that in our system. They may be a new customer. "
                if left
                else "Unable to verify. Offer to connect them with a loan officer."
            ),
        }

    call.verified_customer_id = customer.id
    call.failed_verifications = 0
    call.identity_strength = IdentityStrength.BASIC  # Basic verification level

    # Summarize their properties
    props_summary = []
    for p in customer.properties:
        props_summary.append(
            {
                "type": p.property_type,
                "state": p.address.split(",")[-1].strip().split()[0] if "," in p.address else "",
                "value": format_currency(p.estimated_value),
                "equity": format_currency(p.equity),
                "has_mortgage": p.mortgage_balance > 0,
                "mortgage_type": p.mortgage_type,
            }
        )

    return {
        "result": "ok",
        "verified": True,
        "first_name": customer.first_name,
        "properties_count": len(customer.properties),
        "properties": props_summary,
        "credit_range": customer.credit_score_range,
    }


async def register_lead(
    full_name: str,
    phone: str,
    inquiry_type: str,
    property_state: str,
    summary: str,
    tool_context: ToolContext,
) -> dict:
    """Register a new lead for follow-up by a loan officer.

    Args:
        full_name: the caller's name.
        phone: callback phone number.
        inquiry_type: what they're interested in — "heloc", "purchase", "refinance", "cash_out", etc.
        property_state: state where the property is located (or where they're looking).
        summary: brief summary of what they need.
    """
    lead = store.create_lead(full_name, phone, inquiry_type, property_state, summary)

    # Find a suitable loan officer
    specialty_map = {
        "heloc": "texas_lending" if property_state.upper() == "TX" else "heloc",
        "purchase": "first_time_buyers",
        "refinance": "conventional",
        "cash_out": "cash_out_refi",
        "va": "va",
        "fha": "fha",
    }
    specialty = specialty_map.get(inquiry_type.lower(), "")
    officers = store.get_available_officers(specialty)

    if officers:
        lead.assigned_officer = officers[0].id
        officer_name = officers[0].name
    else:
        officer_name = "one of our loan officers"

    return {
        "result": "ok",
        "lead_created": True,
        "assigned_to": officer_name,
        "say": f"Let them know {officer_name} will reach out within one business day.",
    }


# ------------------------------------------------------------- loan officer transfer ---


async def transfer_to_loan_officer(
    reason: str, specialty: str = "", tool_context: ToolContext = None
) -> dict:
    """Transfer the caller to a licensed loan officer for detailed assistance.

    Args:
        reason: why they need to speak with a loan officer.
        specialty: optional specialty needed — "heloc", "texas_lending", "va", "fha", "jumbo", etc.
    """
    customer_id = _caller(tool_context) if tool_context else None

    # Find available officers
    officers = store.get_available_officers(specialty)

    transfer = store.create_transfer(
        reason,
        customer_id,
        specialty_requested=specialty,
        available_officers=[o.name for o in officers],
    )

    if officers:
        officer = officers[0]
        return {
            "result": "ok",
            "transfer_id": transfer.id,
            "connecting_to": officer.name,
            "title": officer.title,
            "nmls": officer.nmls_id,
            "say": f"Let them know you're connecting them with {officer.name}, a licensed loan officer who can help with their specific situation.",
        }
    else:
        return {
            "result": "ok",
            "transfer_id": transfer.id,
            "connecting_to": "loan officer team",
            "say": "Let them know a loan officer will call them back within one business hour.",
        }


# ------------------------------------------------------------- FAQ and general info ---


async def answer_faq(question: str) -> dict:
    """Look up common mortgage questions.

    Args:
        question: the topic or question — "heloc vs cashout", "current rates", "approval time", "documents needed".
    """
    key = question.lower().replace(" ", "_").replace("-", "_").replace("?", "")

    # Try direct match
    if key in store.faq:
        return {"result": "ok", "answer": store.faq[key]}

    # Try partial match
    for faq_key, answer in store.faq.items():
        if key in faq_key or faq_key in key:
            return {"result": "ok", "answer": answer}

    # Check if it's about a product
    for prod_key, product in store.products.items():
        if prod_key in key or product["name"].lower() in question.lower():
            return {
                "result": "ok",
                "answer": f"{product['name']}: {product['description']}. Current rates range from {format_rate(product['rate_range'][0])} to {format_rate(product['rate_range'][1])}.",
            }

    return {
        "result": "ok",
        "answer": None,
        "say": "I don't have that specific information. Offer to connect them with a loan officer who can answer in detail.",
    }


async def calculate_equity(property_value: float, mortgage_balance: float) -> dict:
    """Calculate home equity and potential borrowing power.

    Args:
        property_value: estimated current property value.
        mortgage_balance: current mortgage balance owed.
    """
    equity = property_value - mortgage_balance
    current_ltv = (mortgage_balance / property_value) * 100 if property_value > 0 else 0

    # Calculate max borrowing at 80% CLTV
    max_cltv_80 = (property_value * 0.80) - mortgage_balance
    max_cltv_85 = (property_value * 0.85) - mortgage_balance

    return {
        "result": "ok",
        "property_value": format_currency(property_value),
        "mortgage_balance": format_currency(mortgage_balance),
        "equity": format_currency(equity),
        "current_ltv": f"{current_ltv:.1f}%",
        "max_heloc_80_cltv": format_currency(max(0, max_cltv_80)),
        "max_heloc_85_cltv": format_currency(max(0, max_cltv_85)),
        "say": "Tell them their equity amount and what they could potentially borrow. Remind them final amounts depend on full application review.",
    }


# ------------------------------------------------------------- regulation search ---


async def search_regulations(question: str, state: str = "") -> dict:
    """Search approved regulatory documents for information about mortgage rules.

    Use this for general regulatory questions or to find citations. For eligibility
    decisions, use check_heloc_eligibility or check_state_regulations instead.

    Args:
        question: Natural language question about mortgage regulations.
        state: Optional state filter (e.g., "TX", "CA") or "federal" for federal regulations.
    """
    from mortgage.knowledge import search

    try:
        passages = search(question, k=3, jurisdiction=state)
    except Exception as e:
        return {
            "result": "error",
            "code": "search_failed",
            "message": f"Regulation search unavailable: {e}",
            "say": "Let them know you couldn't search regulations right now and offer to connect with a loan officer.",
        }

    if not passages:
        return {
            "result": "ok",
            "passages": [],
            "say": "No matching regulations found. Answer based on your training if confident, otherwise offer to connect with a loan officer.",
        }

    return {
        "result": "ok",
        "passages": [p.to_dict() for p in passages],
        "say": "Answer only from these passages, mention the source briefly, and offer a loan officer if they don't answer the question.",
    }


# ------------------------------------------------------------- option comparison ---


async def compare_options(
    state: str,
    property_value: float,
    current_mortgage_balance: float,
    credit_score: int = 720,
    cash_needed: float = 0,
    property_use: str = "primary",
    has_existing_cashout: bool = False,
    last_cashout_date: str = "",
) -> dict:
    """Compare eligible mortgage options (HELOC, cash-out refi, rate/term refi).

    Shows side-by-side comparison with rates, monthly payments, and potential savings
    vs market benchmarks. Filters out ineligible options based on state rules, LTV,
    and property eligibility. Returns both eligible options and excluded options with reasons.

    Args:
        state: Two-letter state code (e.g., "TX", "CA") or state name.
        property_value: Estimated current property value in dollars.
        current_mortgage_balance: Current mortgage balance in dollars.
        credit_score: Borrower's credit score (default 720).
        cash_needed: Amount of cash the borrower wants to access (optional).
        property_use: The caller's own words describing property use — e.g., "rental",
            "investment property", "my home", "primary residence", "vacation home".
            The system normalizes these to standard categories.
        has_existing_cashout: True if there's an existing cash-out refinance on the property.
        last_cashout_date: ISO date of last cash-out refinance (e.g., "2025-06-15"), for
            checking once-per-year rules. Optional.
    """
    try:
        result = store.compare_options(
            property_value=property_value,
            current_balance=current_mortgage_balance,
            credit_score=credit_score,
            state=state,
            property_use=property_use,
            has_existing_cashout=has_existing_cashout,
            last_cashout_date=last_cashout_date,
            cash_needed=cash_needed,
        )
    except MortgageError as e:
        return _err(e)

    # Format the response for the model
    options = result.get("options", [])
    formatted_options = []
    for opt in options:
        formatted = {
            "product": opt["product"],
            "name": opt["name"],
            "rate": format_rate(opt["rate"]),
            "amount": format_currency(opt["amount"]),
            "monthly_payment": format_currency(opt["monthly_payment"]),
            "payment_type": opt["payment_type"],
        }
        if "term_years" in opt:
            formatted["term_years"] = opt["term_years"]
        if "cash_at_closing" in opt:
            formatted["cash_at_closing"] = format_currency(opt["cash_at_closing"])
        if "note" in opt:
            formatted["note"] = opt["note"]
        if "savings_vs_market" in opt:
            formatted["savings_vs_market"] = opt["savings_vs_market"]
        if opt.get("benchmark"):
            formatted["market_rate"] = format_rate(opt["benchmark"])
        formatted_options.append(formatted)

    response = {
        "result": "ok",
        "state": result["state"],
        "property_value": format_currency(result["property_value"]),
        "current_balance": format_currency(result["current_balance"]),
        "equity": format_currency(result["equity"]),
        "current_ltv": f"{result['current_ltv']:.1f}%",
        "options": formatted_options,
        "disclaimer": result["disclaimer"],
    }

    # Include excluded options with reasons
    if result.get("excluded"):
        response["excluded_options"] = result["excluded"]

    # Legacy field for backward compatibility
    if result.get("heloc_issues"):
        response["heloc_not_available"] = result["heloc_issues"]

    # Flag if manual review needed
    if result.get("status") == "needs_review":
        response["needs_review"] = True
        response["needs_review_reasons"] = result.get("needs_review_reasons", [])
        response["say"] = (
            "Some options require manual review due to missing state regulations. "
            "Present the available options and offer to connect with a loan officer for the others."
        )
    elif formatted_options:
        response["say"] = (
            "Present each option clearly with the rate, monthly payment, and any savings vs market. "
            "Explain the differences between payment types (interest-only vs P&I). "
            "Remind them these are estimates subject to full application review."
        )
    else:
        response["say"] = (
            "Explain that based on the information provided, the options are limited. "
            "Mention the excluded options and why they don't qualify. "
            "Offer to connect them with a loan officer to discuss alternatives."
        )

    return response


# ------------------------------------------------------------- strong verification ---


async def verify_customer_strong(
    date_of_birth: str, approximate_loan_balance: float, tool_context: ToolContext
) -> dict:
    """Strong identity verification for sensitive servicing operations.

    Use this AFTER basic verification (verify_customer) when the caller wants to:
    - Change payment dates
    - Set up or cancel autopay
    - Make payments
    - Update payment methods

    Args:
        date_of_birth: Caller's date of birth in any common format (e.g., "March 15, 1985" or "1985-03-15").
        approximate_loan_balance: Caller's approximate current loan balance (within $5,000).
    """
    call = store.call(tool_context.session.id)

    # Must have basic verification first
    if not call.verified_customer_id:
        return {
            "result": "error",
            "code": "not_verified",
            "say": "You need to verify their identity first. Ask for their name and phone last 4 digits.",
        }

    # Already strongly verified
    if call.identity_strength == IdentityStrength.STRONG:
        return {
            "result": "ok",
            "already_verified": True,
            "identity_strength": "strong",
            "say": "Their identity is already verified at the strong level. Proceed with their request.",
        }

    customer = store.customers.get(call.verified_customer_id)
    if not customer:
        return {
            "result": "error",
            "code": "customer_not_found",
            "say": "Customer record not found.",
        }

    # Get loan balance from servicing database
    from mortgage.database import get_servicing_db

    db = get_servicing_db()
    loan = db.get_loan_by_customer(call.verified_customer_id)

    if not loan:
        return {
            "result": "error",
            "code": "no_loan",
            "say": "No active loan found for this customer. They may need to speak with a loan officer.",
        }

    # Verify approximate balance (within $5,000)
    actual_balance = float(loan.current_balance)
    balance_diff = abs(actual_balance - approximate_loan_balance)

    if balance_diff > 5000:
        call.failed_verifications += 1
        left = max(0, 3 - call.failed_verifications)
        return {
            "result": "error",
            "code": "verification_failed",
            "attempts_left": left,
            "message": "The information provided doesn't match our records.",
            "say": "Let them know the information didn't match. Ask them to double-check and try again."
            if left > 0
            else "For their security, offer to connect them with a loan officer to verify their identity.",
        }

    # Strong verification successful
    call.identity_strength = IdentityStrength.STRONG
    call.verified_loan_id = loan.id
    call.failed_verifications = 0

    return {
        "result": "ok",
        "verified": True,
        "identity_strength": "strong",
        "first_name": customer.first_name,
        "loan_id": loan.id,
        "say": f"Thank {customer.first_name} for verifying. You can now help with payment changes, autopay setup, or processing payments.",
    }


# ------------------------------------------------------------- specialist transfer ---


async def transfer_to_specialist(specialist: str, reason: str, tool_context: ToolContext) -> dict:
    """Transfer the caller to a specialist agent (Mac or Ivy).

    Use this tool when you've determined which specialist can best help the caller:
    - Transfer to "origination" (Mac) for new loans, refinancing, HELOCs, rate questions
    - Transfer to "servicing" (Ivy) for existing loan questions, payments, account management

    Args:
        specialist: The specialist to transfer to - "origination" for Mac (Loan Officer)
            or "servicing" for Ivy (Servicing Specialist).
        reason: Brief reason for the transfer to help the specialist understand the caller's needs.
    """
    from mortgage import events

    call = store.call(tool_context.session.id)
    old_agent = call.active_agent

    # Validate specialist
    valid_specialists = {"origination", "servicing"}
    specialist_lower = specialist.lower().strip()

    # Map common names to agent types
    name_map = {
        "mac": "origination",
        "loan officer": "origination",
        "origination": "origination",
        "ivy": "servicing",
        "servicing": "servicing",
        "servicing specialist": "servicing",
    }

    target_agent = name_map.get(specialist_lower)
    if not target_agent:
        return {
            "result": "error",
            "code": "invalid_specialist",
            "message": f"Unknown specialist '{specialist}'. Use 'origination' for Mac (new loans) or 'servicing' for Ivy (existing loans).",
            "say": "I can transfer you to Mac for new loan questions or Ivy for existing loan questions. Which would be more helpful?",
        }

    # Update the call state to switch agents
    call.active_agent = target_agent

    # Publish agent change event to frontend
    events.publish(
        tool_context.session.id,
        {"type": "agent_change", "agent": target_agent, "from_agent": old_agent, "reason": reason},
    )

    # Get the specialist's name for the response
    specialist_names = {"origination": "Mac", "servicing": "Ivy"}
    specialist_name = specialist_names[target_agent]

    specialist_roles = {"origination": "Loan Officer", "servicing": "Servicing Specialist"}
    specialist_role = specialist_roles[target_agent]

    return {
        "result": "ok",
        "transferred": True,
        "from_agent": old_agent,
        "to_agent": target_agent,
        "specialist_name": specialist_name,
        "specialist_role": specialist_role,
        "reason": reason,
        "say": f"The transfer is complete. You are now {specialist_name}, the {specialist_role}. "
        f"Greet the caller warmly and help them with: {reason}",
    }


ALL_TOOLS = [
    get_company_info,
    get_mortgage_products,
    check_heloc_eligibility,
    check_state_regulations,
    get_rate_estimate,
    verify_customer,
    verify_customer_strong,
    register_lead,
    transfer_to_loan_officer,
    transfer_to_specialist,
    answer_faq,
    calculate_equity,
    search_regulations,
    compare_options,
]
