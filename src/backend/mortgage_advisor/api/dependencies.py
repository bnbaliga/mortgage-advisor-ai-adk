"""Shared runtime objects for the API: the ADK runner, sessions and live config.

Built once per process. Routes import these instead of creating their own.
"""
from google.adk.agents.run_config import StreamingMode
from google.adk.runners import RunConfig, Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from mortgage_advisor.agent import tools
from mortgage_advisor.agent.agent import root_agent
from mortgage_advisor.core.config import APP_NAME, VOICE
from mortgage_advisor.services.origination import MortgageStore
from mortgage_advisor.services.usage import COMPRESSION_TRIGGER

session_service = InMemorySessionService()
runner = Runner(app_name=APP_NAME, agent=root_agent, session_service=session_service)

RUN_CONFIG = RunConfig(
    streaming_mode=StreamingMode.BIDI,
    response_modalities=["AUDIO"],
    speech_config=types.SpeechConfig(voice_config=types.VoiceConfig(
        prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=VOICE))),
    input_audio_transcription=types.AudioTranscriptionConfig(),
    output_audio_transcription=types.AudioTranscriptionConfig(),
    context_window_compression=types.ContextWindowCompressionConfig(
        trigger_tokens=COMPRESSION_TRIGGER, sliding_window=types.SlidingWindow(target_tokens=60_000)),
)


def get_store() -> MortgageStore:
    """The origination store the tools use (swappable in tests via tools.use_store)."""
    return tools.store
