"""Task category definitions for prompt classification."""

from __future__ import annotations

from enum import Enum


class TaskCategory(str, Enum):
    SIMPLE_CHAT = "simple_chat"
    GENERAL_CHAT = "general_chat"
    CODING = "coding"
    ANALYSIS = "analysis"
    CREATIVE_WRITING = "creative_writing"
    SUMMARIZATION = "summarization"
    TRANSLATION = "translation"
    MATH = "math"
    VISION = "vision"
    FUNCTION_CALLING = "function_calling"
    LONG_CONTEXT = "long_context"
