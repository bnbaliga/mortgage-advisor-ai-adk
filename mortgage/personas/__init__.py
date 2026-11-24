"""Agent personas for the mortgage lifecycle.

Each persona defines the personality, capabilities, and constraints for a
specific agent role:

- Sam (Triage): Customer Representative for initial triage and routing
- Mac (Origination): AI Mortgage Advisor for new loans and inquiries
- Ivy (Servicing): AI Servicing Specialist for existing loan management
- Collections (Future): Early and late stage collections
- Welcome (Future): New borrower onboarding
"""

from mortgage.personas.origination import AGENT_NAME as MAC_NAME
from mortgage.personas.origination import MAC_INSTRUCTION
from mortgage.personas.servicing import AGENT_NAME as IVY_NAME
from mortgage.personas.servicing import IVY_INSTRUCTION
from mortgage.personas.triage import AGENT_NAME as SAM_NAME
from mortgage.personas.triage import SAM_INSTRUCTION

__all__ = [
    "SAM_INSTRUCTION",
    "SAM_NAME",
    "MAC_INSTRUCTION",
    "MAC_NAME",
    "IVY_INSTRUCTION",
    "IVY_NAME",
]
