"""
Markus AI — Speech Package
"""

from speech.vad import VoiceActivityDetector
from speech.conversation_state import ConversationStateMachine, ConversationState, InvalidTransitionError
from speech.stt import stt_engine, SpeechToText
from speech.tts import tts_engine, TextToSpeech
from speech.wakeword import wakeword_detector, WakeWordDetector
from speech.service import voice_service, VoiceService

__all__ = [
    "VoiceActivityDetector",
    "ConversationStateMachine",
    "ConversationState",
    "InvalidTransitionError",
    "stt_engine",
    "SpeechToText",
    "tts_engine",
    "TextToSpeech",
    "wakeword_detector",
    "WakeWordDetector",
    "voice_service",
    "VoiceService",
]
