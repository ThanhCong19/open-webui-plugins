"""
title: Keep reasoning_content (within and across turns)
author: @Classic298 / @clsc
description: Monkey-patches middleware.get_reasoning_format so any non-ollama model returns 'reasoning_content' instead of None. Catches every reasoning_format call site at once (the in-turn tool-call loop rebuilds AND the cross-turn history rebuild at middleware.py:2385). Result: reasoning is preserved both within a turn's tool-call loop and across turns on prior assistant messages, so reasoning models can reference their own previous chain of thought. Use excluded_model_ids to opt specific models out (e.g. Gemma family). Leaves ollama (think_tags) untouched. Filter must be enabled so __init__ runs and installs the patch. Container restart required to remove the patch.
required_open_webui_version: 0.9.5
version: 2.0.0
"""

from typing import Optional
from pydantic import BaseModel, Field

_PATCH_VERSION = "2.0.0"
_EXCLUDED_IDS: set[str] = set()


def _install_grf_patch():
    from open_webui.utils import middleware as _mw

    if not hasattr(_mw, "_rk_pristine_grf"):
        _mw._rk_pristine_grf = _mw.get_reasoning_format
    if getattr(_mw, "_rk_version", None) == _PATCH_VERSION:
        return
    _mw._rk_version = _PATCH_VERSION

    orig = _mw._rk_pristine_grf

    def patched(model):
        result = orig(model)
        if result == 'think_tags':
            return result
        if model.get('id') in _EXCLUDED_IDS:
            return result
        return 'reasoning_content'

    _mw.get_reasoning_format = patched


class Filter:
    class Valves(BaseModel):
        priority: int = Field(default=0, description="Lower runs first.")
        excluded_model_ids: str = Field(
            default="",
            description="Comma-separated model IDs to skip (e.g. 'gemma-4-it' for models whose chat template forbids reasoning in history). Excluded models keep the original get_reasoning_format behaviour (None for non-ollama, non-llama.cpp connections).",
        )

    def __init__(self):
        self.valves = self.Valves()
        _install_grf_patch()

    async def inlet(self, body: dict, __model__: Optional[dict] = None) -> dict:
        global _EXCLUDED_IDS
        _EXCLUDED_IDS = {
            mid.strip() for mid in self.valves.excluded_model_ids.split(",") if mid.strip()
        }
        return body
