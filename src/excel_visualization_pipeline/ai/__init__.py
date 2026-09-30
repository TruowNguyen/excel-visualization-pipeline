"""Evidence-grounded AI analysis for committed CX data."""

from .analytics import AnalyticsEngine, TrendComputation, TrendStrategy
from .config import AIConfig
from .evidence import EvidenceBuilder
from .llm import (
    DisabledLLMAdapter,
    LLMAdapter,
    LLMResult,
    NineRouterLLMAdapter,
    ProviderError,
)
from .repository import AnalysisSnapshotRepository
from .service import AIApplicationService, PromptRegistry
from .validation import OutputValidator

__all__ = [
    "AIApplicationService",
    "AIConfig",
    "AnalysisSnapshotRepository",
    "AnalyticsEngine",
    "DisabledLLMAdapter",
    "EvidenceBuilder",
    "LLMAdapter",
    "LLMResult",
    "NineRouterLLMAdapter",
    "OutputValidator",
    "PromptRegistry",
    "ProviderError",
    "TrendComputation",
    "TrendStrategy",
]
