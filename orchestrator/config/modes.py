"""
HeartBeat Engine - Chat Modes Registry

Maps hockey-specific chat modes to OpenRouter model slugs and defaults.
These mappings enable runtime selection of the most appropriate model for
each specialized task without changing API responses or orchestration nodes.
"""

from typing import Dict, Any


class ModeRegistry:
    """Central registry for chat modes and model selections."""

    def __init__(self) -> None:
        # Primary selections with conservative, high-quality defaults.
        self._modes: Dict[str, Dict[str, Any]] = {
            # General team/player analytics synthesis
            "general": {
                "primary": "anthropic/claude-sonnet-4.5",
                "fallbacks": [
                    "openai/gpt-4.1-mini",
                    "meta/llama-3.1-405b-instruct",
                ],
                "generation": {"temperature": 0.2, "max_tokens": 2048, "top_p": 0.95},
            },
            # Visual/video analysis narratives over tool outputs
            "visual_analysis": {
                "primary": "anthropic/claude-3.7-sonnet",
                "fallbacks": ["openai/gpt-4o-mini"],
                "generation": {"temperature": 0.3, "max_tokens": 2048},
            },
            # Contract predictions, financial reports, cap/market analytics
            "contract_finance": {
                "primary": "openai/o4-mini",
                "fallbacks": ["mistralai/mistral-large"],
                "generation": {"temperature": 0.2, "max_tokens": 2048},
            },
            # Fast, inexpensive responses (non-critical)
            "fast": {
                "primary": "openai/gpt-4o-mini",
                "fallbacks": ["google/gemini-2.0-flash-thinking-exp"],
                "generation": {"temperature": 0.2, "max_tokens": 1024},
            },
            # Pre-scout report mode: structured, longer synthesis with evidence
            "report": {
                "primary": "openai/o4-mini-deep-research",
                "fallbacks": ["openai/o4-mini", "anthropic/claude-3.7-sonnet"],
                "generation": {"temperature": 0.2, "max_tokens": 3072, "top_p": 0.95},
            },
        }

        # Allowlist for direct user-provided model overrides
        self._allowlist = set()
        for v in self._modes.values():
            self._allowlist.add(v["primary"])
            for f in v.get("fallbacks", []):
                self._allowlist.add(f)

    def resolve(self, mode: str | None, explicit_model: str | None = None) -> Dict[str, Any]:
        """
        Resolve the model and generation params for the requested mode/model.
        If explicit_model is provided, validate against allowlist.
        """
        if explicit_model:
            if explicit_model not in self._allowlist:
                raise ValueError("Requested model is not allowed")
            return {
                "model": explicit_model,
                "generation": {"temperature": 0.2, "max_tokens": 2048, "top_p": 0.95},
            }

        key = (mode or "general").lower()
        cfg = self._modes.get(key) or self._modes["general"]
        return {"model": cfg["primary"], "generation": cfg.get("generation", {})}


# Global registry instance
modes = ModeRegistry()


