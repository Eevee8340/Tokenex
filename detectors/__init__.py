from .base import BaseDetector
from .opencode import OpencodeDetector
from .codex import CodexDetector
from .gemini_cli import GeminiCLIDetector
from .antigravity import AntigravityDetector

ALL_DETECTORS = [
    OpencodeDetector,
    CodexDetector,
    GeminiCLIDetector,
    AntigravityDetector,
]

__all__ = [
    "BaseDetector",
    "OpencodeDetector",
    "CodexDetector",
    "GeminiCLIDetector",
    "AntigravityDetector",
    "ALL_DETECTORS",
]
