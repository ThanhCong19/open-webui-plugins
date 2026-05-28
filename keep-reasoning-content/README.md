# 🧠 Keep reasoning_content (within and across turns)

Stops Open WebUI dropping `reasoning_content` on its way to your reasoning model. Works with any OpenAI-compatible model that emits `delta.reasoning_content` in its streaming response, so DeepSeek / Kimi / MiMo / vLLM actually have their prior chain of thought during tool-call loops and across follow-up turns.

> [!IMPORTANT]
> **Supported Open WebUI versions: `0.9.5` only.** This filter patches internal middleware functions whose names and line positions are specific to 0.9.5. Newer Open WebUI versions may/will probably need updates to this filter.

> [!TIP]
> **🚀 [Jump to Installation](#-installation)** — under 1 minute, no container restart needed for a fresh install.

## ⚠️ The problem this fixes

If you've seen one of these, this filter is for you:

- `reasoning_content is missing in assistant tool call message at index N` (HTTP 400 from the provider mid tool-call)
- Your reasoning model "forgetting" why it called a tool earlier in the same turn
- Cross-turn follow-ups where the model claims it has no memory of its prior reasoning

Open WebUI's `get_reasoning_format` returns `None` for every connection except those explicitly flagged `ollama` or `llama.cpp`. That `None` makes `convert_output_to_messages` drop `reasoning_content` from the rebuilt message history. The data is in storage. It just never reaches the model.

## 🎯 Works with

Any OpenAI-compatible reasoning model whose API emits `delta.reasoning_content` in its SSE stream:

- DeepSeek (R1, V3.x reasoner, V4 flash/pro)
- Kimi K2.5 / Moonshot
- Xiaomi MiMo (V2.5, V2-Pro, Omni)
- vLLM serving any reasoning model
- OpenRouter passthrough to any of the above
- Anything else with the same convention

Not needed if your connection's Provider is already set to `llama.cpp` (already correct). Skipped automatically for connections flagged `ollama` (those need inline `<think>` tags, not the `reasoning_content` field).

## ✅ How it works

The filter monkey-patches `middleware.get_reasoning_format` so any non-ollama model returns `'reasoning_content'` instead of `None`. That single change catches every reasoning-format call site at once:

- The cross-turn history rebuild at `middleware.py:2385` (which runs **before** any filter inlet hook, so a per-request model dict mutation cannot reach it)
- The in-turn tool-call loop rebuilds at `middleware.py:4788`, `:4793`, and `:5015`

The result is `reasoning_content` emitted as a top-level field on every prior assistant message in the request body, which is exactly what these providers' APIs require per their own documentation (see MiMo's passing-back-`reasoning_content` guide for a concrete example).

No routing side effects: the other `provider == 'llama.cpp'` checks in the Open WebUI codebase read from the connection's `api_config`, not from this function, so request dispatch is unaffected.

## 🧪 Validated

End-to-end against MiMo-v2.5 with both in-loop tool calling (three native tool calls within a single turn) and cross-turn follow-ups (the specific numbers MiMo committed to in its turn-1 reasoning, e.g. `742,385`, appeared verbatim in the turn-2 outgoing HTTP body as `payload[1].reasoning_content`). Same code path validated within-turn on DeepSeek.

## Components

| File | Type | Install location |
|------|------|-----------------|
| `filter.py` | Filter | Admin Panel → Functions |

## 📦 Installation

1. Copy the contents of `filter.py`, or click **Get** on the Community page.
2. In Open WebUI, go to **Admin Panel → Functions → + New** and paste the code, then **Save**.
3. Toggle the function on.
4. Either set it as **Global** (applies to every model on the instance) or attach it per-model under **Model settings → Filters**. Both work; the patch is module-level once installed.

No container restart needed for a fresh install.

## ⚙️ Configuration

Two valves:

- **`priority`** (int, default `0`) — filter sort order. Lower numbers run first. Leave at `0` unless you stack multiple filters and need a specific order.
- **`excluded_model_ids`** (string, default empty) — comma-separated list of model IDs to opt **out** of the patch. Use for models whose chat template explicitly forbids reasoning in history (the Gemma 4 family is the main example). Excluded models keep Open WebUI's original `get_reasoning_format` behaviour. Format: `gemma-4-it,gemma-4-9b,other-model-id`.

Valve changes take effect on the next request after you save.

## 🔁 Upgrading and uninstalling

- **Upgrading to a new version:** paste the new code and save. The install logic is version-tagged and replaces the wrappers cleanly without needing a container restart.
- **Fully removing the patch:** disable the filter **and restart the container**. The wrapped function lives in the middleware module's globals for the lifetime of the Python process, so a filter-disable alone leaves the wrapper in place (harmless, but it stays).

## ❓ FAQ

**Will this affect my non-reasoning models (GPT-4o, plain Claude, etc.)?**
No. Those models do not emit `delta.reasoning_content` in their streaming response, so the output accumulator never gets reasoning items, and the patched function has nothing to emit. It is a no-op for them in practice.

**Why is `'llama.cpp'` the magic string?**
Internal Open WebUI naming. The code branch labelled `'llama.cpp'` is the one that emits `reasoning_content` as a top-level message field, because llama.cpp's OpenAI-compatible server was the upstream that introduced this convention. The label is misleading; this filter has nothing to do with the llama.cpp inference engine specifically. It applies to any OpenAI-compatible reasoning model.

**What about Claude / extended thinking?**
Claude uses its own `thinking_blocks` shape, not OpenAI-style `reasoning_content`, and routes through a different handler entirely. This filter does not touch Claude's path.

**Will the model actually USE the replayed reasoning?**
Mechanically the filter delivers it on every relevant request. Whether the model uses it depends on its training. Some models (notably DeepSeek and MiMo) have honesty-training that may make them disclaim memory of their own prior reasoning even when it is present in context. That is a model-behaviour question, not something a filter can change.

**Does this work on Open WebUI < 0.9.5?**
Untested on earlier versions. The line numbers and function signatures above refer to 0.9.5; earlier versions may have differently-named or differently-located internals.

## 📝 Changelog

- **2.0.0** — Cross-turn coverage via `get_reasoning_format` monkey-patch. Added `excluded_model_ids` valve. Catches the pre-inlet history rebuild that v1 missed.
- **1.0.0** — Initial release. Within-turn tool-call loop only, via inlet `model['provider']` flip. Superseded by 2.0.0.

## 🙏 Credits

Huge thanks to [@cbwln](https://github.com/cbwln) on GitHub (or here on the Community) for hands-on testing during development and for the wire-payload validation runs that confirmed the cross-turn fix end-to-end on MiMo-v2.5 and DeepSeek-v4-flash.
