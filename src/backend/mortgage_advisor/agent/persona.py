"""Dynamic persona switching for the AI Mortgage Advisor.

The instruction is a FUNCTION, not a string: ADK calls it every turn, so:
- "today" is always today
- The active agent persona can change mid-call
- Observer suggestions are injected into the prompt

Policy is deliberately NOT in here — see policy.py. The persona
only says "always try the tool; the system decides".
"""
import os
from datetime import timedelta
from typing import Optional

from google.adk.agents.readonly_context import ReadonlyContext

from mortgage_advisor.agent import tools
from mortgage_advisor.agent.personas.origination import MAC_INSTRUCTION, AGENT_NAME as MAC_NAME
from mortgage_advisor.agent.personas.servicing import IVY_INSTRUCTION, OBSERVER_SUGGESTIONS_FORMAT, AGENT_NAME as IVY_NAME

# Default agent name for API (Mac is the default origination agent)
AGENT_NAME = MAC_NAME

# Environment overrides
ACCENT = os.getenv("MORTGAGE_ACCENT", "").strip()

_ACCENT_SECTION = """
ACCENT AND LANGUAGE
- Speak English with a natural, warm {accent} accent, rhythm and phrasing.
- If the caller switches language, try to accommodate. Keep numbers and terms especially clear.
"""


def get_call_state(ctx: Optional[ReadonlyContext]):
    """Get the CallState for the current session."""
    if ctx is None:
        return None

    session_id = getattr(ctx, 'session_id', None)
    if session_id is None:
        # Try to get from session object
        session = getattr(ctx, 'session', None)
        if session:
            session_id = getattr(session, 'id', None)

    if session_id:
        return tools.store.call(session_id)
    return None


def format_observer_suggestions(suggestions: list) -> str:
    """Format observer suggestions for injection into persona."""
    if not suggestions:
        return ""

    formatted = "\n".join(f"- {s}" for s in suggestions)
    return OBSERVER_SUGGESTIONS_FORMAT.format(suggestions=formatted)


def instruction(ctx: ReadonlyContext | None = None) -> str:
    """Generate the instruction for the current turn.

    Called by ADK on every turn. Dynamically selects the persona based on
    CallState.active_agent and injects observer suggestions.
    """
    # Get current state
    call_state = get_call_state(ctx)
    today = tools.store.today()
    company = tools.store.info["name"]

    # Determine which persona to use
    active_agent = call_state.active_agent if call_state else "origination"

    # Select persona instruction
    if active_agent == "servicing":
        base = IVY_INSTRUCTION
        agent_name = IVY_NAME
    elif active_agent == "collections":
        # Future: Add collections persona
        base = IVY_INSTRUCTION  # Fallback to Ivy for now
        agent_name = IVY_NAME
    elif active_agent == "welcome":
        # Future: Add welcome persona
        base = IVY_INSTRUCTION  # Fallback to Ivy for now
        agent_name = IVY_NAME
    else:
        # Default: origination (Mac)
        base = MAC_INSTRUCTION
        agent_name = MAC_NAME

    # Format observer suggestions
    observer_suggestions = ""
    if call_state and call_state.observer_suggestions:
        observer_suggestions = format_observer_suggestions(call_state.observer_suggestions)

    # Format the instruction
    formatted_today = f"{today:%A, %B} {today.day}, {today.year} ({today.isoformat()})"

    text = base.format(
        agent=agent_name,
        company=company,
        today=formatted_today,
        observer_suggestions=observer_suggestions,
    )

    # Add accent if configured
    if ACCENT:
        text += _ACCENT_SECTION.format(accent=ACCENT)

    return text


def get_agent_info(ctx: ReadonlyContext | None = None) -> dict:
    """Get information about the current agent for UI display."""
    call_state = get_call_state(ctx)
    active_agent = call_state.active_agent if call_state else "origination"

    agent_info = {
        "origination": {"name": MAC_NAME, "role": "Mortgage Advisor", "icon": "user"},
        "servicing": {"name": IVY_NAME, "role": "Servicing Specialist", "icon": "headset"},
        "collections": {"name": "Collections", "role": "Collections Specialist", "icon": "phone"},
        "welcome": {"name": "Welcome", "role": "Welcome Specialist", "icon": "star"},
    }

    info = agent_info.get(active_agent, agent_info["origination"])
    info["active_agent"] = active_agent

    if call_state:
        info["identity_strength"] = call_state.identity_strength
        info["verified"] = call_state.verified_customer_id is not None

    return info
