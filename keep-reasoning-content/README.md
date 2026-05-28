# 🧠 Keep reasoning_content (within and across turns)

Stops Open WebUI dropping `reasoning_content` on its way to your reasoning model. Works with any OpenAI-compatible model that emits `delta.reasoning_content` in its streaming response, so DeepSeek / Kimi / MiMo / vLLM actually have their prior chain of thought during tool-call loops and across follow-up turns.

> [!IMPORTANT]
> **Supported Open WebUI versions: `0.9.5` – `0.9.5`.** This filter patches internal middleware functions whose names and line positions are specific to this range, so newer (or older) Open WebUI versions may/will probably need updates to the filter itself. Whenever you upgrade Open WebUI, check the plugin page for a new version of this filter before relying on it.

> [!WARNING]
> **Don't enable this for models that return a reasoning _summary_ instead of their raw chain of thought** (for example OpenAI's o-series / GPT-5 reasoning models, which only expose a short summary over the API). A summary is not the model's real reasoning and must never be replayed to the provider as `reasoning_content` — sending it back can be rejected outright or poison the model's context. Because the patch is installed **process-wide** (it affects every non-ollama model on the instance, not only the ones you attach it to), the only way to protect such a model is to add its ID to `excluded_model_ids` and run the filter as **Global**, or simply not enable this filter on an instance that serves summary-only reasoning models.

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
- **`excluded_model_ids`** (string, default empty) — comma-separated list of model IDs to opt **out** of the patch. Use it for models whose chat template explicitly forbids reasoning in history (the Gemma 4 family is the main example), and for any model that returns a reasoning _summary_ rather than raw reasoning (see the warning near the top of this README). Excluded models keep Open WebUI's original `get_reasoning_format` behaviour. Format: `gemma-4-it,gemma-4-9b,other-model-id`.

Valve changes take effect on the next request after you save.

## 🔁 Upgrading and uninstalling

- **Upgrading to a new version:** paste the new code and save. The install logic is version-tagged and replaces the wrappers cleanly without needing a container restart.
- **Fully removing the patch:** disable the filter **and restart the container**. The wrapped function lives in the middleware module's globals for the lifetime of the Python process, so a filter-disable alone leaves the wrapper in place (harmless, but it stays).

## ❓ FAQ

<details>
<summary><b>Will this affect my non-reasoning models (GPT-4o, plain Claude, etc.)?</b></summary>

No, it's a no-op for them in practice. Non-reasoning models don't emit `delta.reasoning_content` in their stream, so the output accumulator never collects any reasoning items. The patched function still returns `'reasoning_content'` for them, but there's nothing to put in that field, so the outgoing request is unchanged. You can leave the filter on without worrying about your regular chat models.
</details>

<details>
<summary><b>What about models that return a reasoning <em>summary</em> (OpenAI o-series, GPT-5, …)?</b></summary>

**Exclude them, or don't run this filter on that instance.** Some reasoning models never expose their raw chain of thought over the API — they return only a short, post-hoc *summary* of it. That summary is not the model's actual reasoning, and the provider's API will reject it or mis-handle it if you send it back as `reasoning_content`. Because this filter installs its patch **process-wide** (see the Global-vs-per-model entry below), it will try to replay reasoning for those models too unless you opt them out. Add their model IDs to `excluded_model_ids` and run the filter as **Global** so the exclusion is always applied. This is the warning at the top of the README — it matters.
</details>

<details>
<summary><b>Does it matter whether I enable the filter Global or per-model?</b></summary>

Yes, and it's subtler than a normal filter. `__init__` installs the patch into the middleware module's globals, so **once any request runs this filter, the patch is live for the whole worker process** — it changes `get_reasoning_format` for every non-ollama model, not just the ones you attached it to. The per-request `inlet` hook only refreshes the `excluded_model_ids` set. Practical upshot: enable it **Global** so `inlet` runs on every request and your exclusion list is always in force. Enabling it on a single model still patches the entire process, but your exclusions will only reflect whatever the last filter-active request set them to.
</details>

<details>
<summary><b>Will this increase my token usage / context length?</b></summary>

Yes, modestly. Replaying each prior assistant turn's reasoning means those tokens are now included in every follow-up request instead of being dropped. On long conversations with a verbose reasoning model, that adds up. It's the unavoidable trade-off: there's no way to give the model back its prior chain of thought without actually sending the chain of thought.
</details>

<details>
<summary><b>Why monkey-patch the function instead of flipping a flag in <code>inlet</code>?</b></summary>

Because the cross-turn history rebuild at `middleware.py:2385` runs **before** any filter `inlet` hook. A per-request mutation of the model dict in `inlet` can't reach that earlier rebuild, and that rebuild is exactly the path that drops reasoning on follow-up turns. Patching the function itself is the only place that catches both the pre-inlet history rebuild and the in-turn tool-call rebuilds at once. v1 used the `inlet` approach and only ever fixed the within-turn case (see the changelog).
</details>

<details>
<summary><b>Why is <code>'llama.cpp'</code> the magic string?</b></summary>

Internal Open WebUI naming. The code branch labelled `'llama.cpp'` is the one that emits `reasoning_content` as a top-level message field, because llama.cpp's OpenAI-compatible server was the upstream that introduced this convention. The label is misleading: this filter has nothing to do with the llama.cpp inference engine specifically, and there are **no routing side effects** — request dispatch reads the provider from the connection's `api_config`, not from this function. It applies to any OpenAI-compatible reasoning model.
</details>

<details>
<summary><b>What about Claude / extended thinking?</b></summary>

Untouched. Claude uses its own `thinking_blocks` shape, not OpenAI-style `reasoning_content`, and routes through a different handler entirely. This filter never sees Claude's path, so it neither helps nor harms it.
</details>

<details>
<summary><b>Will the model actually <em>use</em> the replayed reasoning?</b></summary>

Mechanically the filter delivers it on every relevant request — that part is verified on the wire (see [Validated](#-validated)). Whether the model *acts* on it depends on its training. Some models (notably DeepSeek and MiMo) have honesty-training that can make them disclaim memory of their own prior reasoning even when it's sitting right there in their context. That's a model-behaviour question, not something a filter can change.
</details>

<details>
<summary><b>I disabled the filter but the behaviour is still there.</b></summary>

Expected. The patch lives in the middleware module's globals for the lifetime of the Python process, so disabling the filter stops `inlet` from running but leaves the wrapped function in place. **Restart the container** to fully remove it — see [Upgrading and uninstalling](#-upgrading-and-uninstalling).
</details>

<details>
<summary><b>Does this work on Open WebUI outside the supported range?</b></summary>

Untested, and likely to need updates. The line numbers and function signatures this filter depends on are specific to the supported version range at the top of this README; earlier or later releases may rename or relocate `get_reasoning_format` and the rebuild call sites. Watch the plugin page for a version bump whenever you upgrade Open WebUI.
</details>

## 📝 Changelog

- **2.0.0** — Cross-turn coverage via `get_reasoning_format` monkey-patch. Added `excluded_model_ids` valve. Catches the pre-inlet history rebuild that v1 missed.
- **1.0.0** — Initial release. Within-turn tool-call loop only, via inlet `model['provider']` flip. Superseded by 2.0.0.

## 🙏 Credits

Huge thanks to [@cbwln](https://github.com/cbwln) on GitHub (or here on the Community) for hands-on testing during development and for the wire-payload validation runs that confirmed the cross-turn fix end-to-end on MiMo-v2.5 and DeepSeek-v4-flash.
