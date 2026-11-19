"""Agent personas for the mortgage lifecycle.

Each persona defines the personality, capabilities, and constraints for a
specific agent role:

- Mac (Origination): AI Mortgage Advisor for new loans and inquiries
- Ivy (Servicing): AI Servicing Specialist for existing loan management
- Collections (Future): Early and late stage collections
- Welcome (Future): New borrower onboarding
"""
from mortgage_advisor.agent.personas.origination import MAC_INSTRUCTION, AGENT_NAME as MAC_NAME
from mortgage_advisor.agent.personas.servicing import IVY_INSTRUCTION, AGENT_NAME as IVY_NAME

__all__ = [
    "MAC_INSTRUCTION",
    "MAC_NAME",
    "IVY_INSTRUCTION",
    "IVY_NAME",
]
