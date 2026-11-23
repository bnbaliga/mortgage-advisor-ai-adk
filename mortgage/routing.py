"""Agent routing logic for multi-persona support.

Routes calls to the appropriate agent persona based on:
- Account state (existing customer with active loan → Ivy)
- Intent detection (payment questions → servicing)
- Explicit handoff requests

Since Google ADK doesn't have native multi-agent support, we implement
routing as dynamic persona switching via CallState.active_agent.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Optional

from mortgage.mortgage import CallState

log = logging.getLogger("mortgage.routing")


class AgentType(Enum):
    """Available agent personas."""
    TRIAGE = "triage"            # Sam - initial triage, routes to specialists
    ORIGINATION = "origination"  # Mac - new loans, inquiries
    SERVICING = "servicing"      # Ivy - existing loan management
    WELCOME = "welcome"          # Welcome calls for new borrowers
    COLLECTIONS = "collections"  # Early/late stage collections


@dataclass
class RoutingDecision:
    """Result of routing logic."""
    agent: AgentType
    reason: str
    silent: bool = True  # True = switch without announcing


# Intent keywords for routing
SERVICING_INTENTS = {
    "balance", "payment", "pay", "autopay", "auto-pay", "due date",
    "payoff", "statement", "escrow", "account", "monthly",
    "change", "update", "card", "bank account", "debit",
}

COLLECTIONS_INTENTS = {
    "late", "past due", "overdue", "missed payment", "behind",
    "forbearance", "hardship", "can't pay", "struggling", "help",
    "payment plan", "arrangement",
}

ORIGINATION_INTENTS = {
    "new loan", "refinance", "refi", "heloc", "home equity",
    "rate", "rates", "purchase", "buy", "buying", "pre-approval",
    "qualify", "eligibility", "credit score",
}


def detect_initial_intent(call: CallState, has_active_loan: bool) -> RoutingDecision:
    """Determine initial agent based on account state.

    Called at the start of a call before any conversation.

    Args:
        call: Current call state
        has_active_loan: Whether the caller has an active loan in servicing

    Returns:
        RoutingDecision with the initial agent
    """
    # Default to triage (Sam) for all new calls
    # Sam will ask qualifying questions and route to the right specialist
    return RoutingDecision(
        agent=AgentType.TRIAGE,
        reason="initial triage for new call",
        silent=True
    )


def detect_intent_from_text(text: str) -> Optional[AgentType]:
    """Detect intent from caller's spoken text.

    Args:
        text: Transcribed caller speech

    Returns:
        AgentType if a clear intent is detected, None otherwise
    """
    text_lower = text.lower()

    # Check for collections-related intents first (highest priority)
    if any(intent in text_lower for intent in COLLECTIONS_INTENTS):
        return AgentType.COLLECTIONS

    # Check for servicing intents
    if any(intent in text_lower for intent in SERVICING_INTENTS):
        return AgentType.SERVICING

    # Check for origination intents
    if any(intent in text_lower for intent in ORIGINATION_INTENTS):
        return AgentType.ORIGINATION

    return None


def should_handoff(call: CallState, detected_intent: Optional[AgentType]) -> Optional[RoutingDecision]:
    """Determine if we should hand off to a different agent.

    Args:
        call: Current call state
        detected_intent: Intent detected from caller's text

    Returns:
        RoutingDecision if handoff is needed, None to stay with current agent
    """
    current = AgentType(call.active_agent)

    # No intent detected, stay with current agent
    if not detected_intent:
        return None

    # Already on the right agent
    if detected_intent == current:
        return None

    # Handoff needed
    return RoutingDecision(
        agent=detected_intent,
        reason=f"intent switched from {current.value} to {detected_intent.value}",
        silent=True
    )


def execute_handoff(call: CallState, decision: RoutingDecision) -> None:
    """Execute a handoff to a new agent persona.

    This updates the CallState which will cause the next instruction()
    call to return the new persona's instructions.

    Args:
        call: Current call state to update
        decision: Routing decision with target agent
    """
    old_agent = call.active_agent
    call.active_agent = decision.agent.value

    log.info("HANDOFF %s -> %s: %s", old_agent, decision.agent.value, decision.reason)


def get_agent_greeting(agent: AgentType, company_name: str, agent_name: str) -> str:
    """Get the appropriate greeting for an agent persona.

    Args:
        agent: The agent type
        company_name: Company name for greeting
        agent_name: Agent's name (Mac, Ivy, Sam, etc.)

    Returns:
        Greeting string for the agent
    """
    if agent == AgentType.TRIAGE:
        return (f"Hi, this is {agent_name} with {company_name}. "
                "How can I help you today?")

    if agent == AgentType.SERVICING:
        return (f"Hi, this is {agent_name} with {company_name} servicing. "
                "This call may be recorded for quality. "
                "May I have your name to pull up your account?")

    if agent == AgentType.COLLECTIONS:
        return (f"Hi, this is {agent_name} with {company_name}. "
                "This call may be recorded for quality. "
                "I'm calling about your mortgage account. May I verify your name?")

    if agent == AgentType.WELCOME:
        return (f"Hi, this is {agent_name} with {company_name}. "
                "Congratulations on your new mortgage! "
                "I'm calling to help you get set up with your account. "
                "Is this a good time?")

    # Default: Origination
    return (f"Hi, this is {agent_name}, your AI Mortgage advisor. "
            "I can answer your mortgage related questions and connect you "
            "with a licensed loan officer. How can I help you today?")
