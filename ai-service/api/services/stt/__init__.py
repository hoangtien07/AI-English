"""Unified streaming speech-to-text service.

Keep package import light so cache verification and the standalone local-STT
smoke do not load optional verifier/fallback engines first.
"""

__all__ = ["STTConfig", "STTModelRegistry", "SessionManager"]


def __getattr__(name: str):
    if name == "STTConfig":
        from api.services.stt.config import STTConfig

        return STTConfig
    if name == "STTModelRegistry":
        from api.services.stt.model_registry import STTModelRegistry

        return STTModelRegistry
    if name == "SessionManager":
        from api.services.stt.session_manager import SessionManager

        return SessionManager
    raise AttributeError(name)
