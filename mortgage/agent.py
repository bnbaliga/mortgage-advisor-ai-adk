"""Mortgage AI Agent: origination + servicing with dynamic persona switching.

The agent supports multiple personas (Mac for origination, Ivy for servicing)
with dynamic switching based on caller needs. All tools are registered, and
the policy layer controls access based on verification level and active agent.

`adk web mortgage` starts the voice agent.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

from google.adk.agents import Agent
from google.adk.models import Gemini
from google.genai import types

from mortgage.persona import instruction
from mortgage.policy import audit, mortgage_gate
from mortgage.servicing_tools import SERVICING_TOOLS
from mortgage.tools import ALL_TOOLS

LIVE_MODEL = os.getenv("LIVE_MODEL", "gemini-3.1-flash-live-preview")
VOICE = os.getenv("MORTGAGE_VOICE") or os.getenv("LIVE_VOICE", "Aoede")

# Combine all tools - origination + servicing
# The policy layer controls which tools are accessible based on active_agent
ALL_AGENT_TOOLS = ALL_TOOLS + SERVICING_TOOLS

root_agent = Agent(
    model=Gemini(
        model=LIVE_MODEL,
        speech_config=types.SpeechConfig(
            voice_config=types.VoiceConfig(
                prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=VOICE)
            )
        ),
    ),
    name="mortgage",
    description="AI Mortgage Agent: handles loan origination (Mac) and servicing (Ivy) with dynamic persona switching.",
    instruction=instruction,
    tools=ALL_AGENT_TOOLS,
    before_tool_callback=mortgage_gate,
    after_tool_callback=audit,
)
