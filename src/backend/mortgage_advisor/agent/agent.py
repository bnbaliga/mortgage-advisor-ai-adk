"""Mortgage AI Agent: origination + servicing with dynamic persona switching.

The agent supports multiple personas (Mac for origination, Ivy for servicing)
with dynamic switching based on caller needs. All tools are registered, and
the policy layer controls access based on verification level and active agent.

`uv run adk web src/backend` starts the agent in the ADK dev UI.
"""
from google.adk.agents import Agent
from google.adk.models import Gemini
from google.genai import types

from mortgage_advisor.agent.persona import instruction
from mortgage_advisor.agent.policy import audit, mortgage_gate
from mortgage_advisor.agent.tools import ALL_TOOLS
from mortgage_advisor.agent.servicing_tools import SERVICING_TOOLS

from mortgage_advisor.core.config import LIVE_MODEL, VOICE

# Combine all tools - origination + servicing
# The policy layer controls which tools are accessible based on active_agent
ALL_AGENT_TOOLS = ALL_TOOLS + SERVICING_TOOLS

root_agent = Agent(
    model=Gemini(
        model=LIVE_MODEL,
        speech_config=types.SpeechConfig(voice_config=types.VoiceConfig(
            prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=VOICE))),
    ),
    name="mortgage",
    description="AI Mortgage Agent: handles loan origination (Mac) and servicing (Ivy) with dynamic persona switching.",
    instruction=instruction,
    tools=ALL_AGENT_TOOLS,
    before_tool_callback=mortgage_gate,
    after_tool_callback=audit,
)
