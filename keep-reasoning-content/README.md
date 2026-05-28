# 🧠 Keep reasoning_content (within and across turns)

Stops Open WebUI dropping `reasoning_content` on its way to your reasoning model. Works with any OpenAI-compatible model that emits `delta.reasoning_content` in its streaming response, so DeepSeek / Kimi / MiMo / vLLM actually have their prior chain of thought during tool-call loops and across follow-up turns.

> [!IMPORTANT]
> **Supported Open WebUI versions: `0.9.5` – `0.9.5`.** This filter patches internal middleware functions whose names and line positions are specific to this range, so newer (or older) Open WebUI versions may/will probably need updates to the filter itself. Whenever you upgrade Open WebUI, check the plugin page for a new version of this filter before relying on it.

> [!WARNING]
> **Enable this filter Globally, and list every reasoning-_summary_ model in the `excluded_model_ids` valve.** Some reasoning models (OpenAI's o-series / GPT-5, and others) never return their raw chain of thought over the API, only a short after-the-fact _summary_. That summary is not real reasoning and must never be replayed to the provider as `reasoning_content`, because sending it back can be rejected outright or poison the model's context. This filter patches Open WebUI **process-wide** and cannot tell those models apart on its own, so you have to name them in the exclusion valve. A per-model install does **not** protect them. See [Recommended setup](#-recommended-setup) for exactly why.

> [!TIP]
> **🚀 [Jump to Recommended setup](#-recommended-setup)** — enable it **Global** and exclude your reasoning-summary models. Install takes under a minute, with no container restart for a fresh install.

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
4. Set it to **Global** so it runs on every request. ([Recommended setup](#-recommended-setup) explains why Global, and why a per-model install is the wrong choice here.)
5. Open the function's valves and add any reasoning-_summary_ models to `excluded_model_ids` (see [Configuration](#-configuration)).

No container restart needed for a fresh install.

## 🛠️ Recommended setup

**Enable the filter Globally, and use `excluded_model_ids` to name any model that returns a reasoning _summary_.** Here is why that exact combination, and not a per-model install, is the correct one.

### The patch is process-wide, not per-model

The filter does not edit one request's payload. On load it **monkey-patches** `middleware.get_reasoning_format`: it replaces a function inside the middleware module itself. From that moment, every call Open WebUI makes to `get_reasoning_format`, for every model in that worker process, hits the patched version. The patch has no notion of which models you "attached" the filter to, because attachment is a per-request concept and the patched function lives one layer below it, in the module's globals.

### Why a per-model install does not work

Attaching the filter to only your reasoning models feels like it should limit the effect to them. It does not. The moment any attached model triggers the load, the patch goes live for the whole process and forces `reasoning_content` on every non-ollama model, including ones you never attached it to. So "I just won't attach it to my summary model" is not protection: that summary model still gets patched as soon as any other model loads the filter. Per-model attachment changes only **which requests run `inlet`**, never **which models the patch touches**.

### Why you must list the exceptions, and why Global makes them reliable

The only way to spare a model from the patch is the exclusion check inside it:

```python
if model.get('id') in _EXCLUDED_IDS:
    return result   # original format -> the patch is a no-op for this model
```

`_EXCLUDED_IDS` is populated from the `excluded_model_ids` valve by the filter's `inlet` hook, and `inlet` only runs on requests where the filter is active. Run it **Global** and `inlet` fires on every request, so the exclusion set is always populated and current, and your summary models are reliably skipped. Run it per-model and `inlet` fires only for the attached models, so the exclusion set can sit empty or stale exactly when a non-attached summary model is being served, and the patch hits it unguarded.

**Bottom line:** Global, plus every reasoning-summary model listed in `excluded_model_ids`. That is the only configuration where the models that should get their reasoning back do, and the models that must not are reliably left alone.

## ⚙️ Configuration

Two valves:

- **`priority`** (int, default `0`) — filter sort order. Lower numbers run first. Leave at `0` unless you stack multiple filters and need a specific order.
- **`excluded_model_ids`** (string, default empty) — comma-separated list of model IDs the patch must **skip**. **Required** for any model that emits reasoning it should not get back: models that return a reasoning _summary_ (OpenAI o-series / GPT-5) and models whose chat template forbids reasoning in history (the Gemma 4 family). Because the patch is process-wide (see [Recommended setup](#-recommended-setup)), listing them here is the only thing that spares them, and the filter must be **Global** for the list to apply on every request. Excluded models keep Open WebUI's original `get_reasoning_format` behaviour. Format: `gemma-4-it,gpt-5,o3-mini`.

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

**List them in `excluded_model_ids` and run the filter Global.** Some reasoning models never expose their raw chain of thought over the API — they return only a short, post-hoc *summary* of it. That summary is not the model's actual reasoning, and the provider's API will reject it or mis-handle it if you send it back as `reasoning_content`. Because this filter installs its patch **process-wide** (see [Recommended setup](#-recommended-setup)), it forces reasoning on those models too unless you opt them out, and *not attaching* the filter to them does nothing to help. Naming them in the exclusion valve is the only reliable protection.
</details>

<details>
<summary><b>Should I enable the filter Global or per-model?</b></summary>

**Global — it has to be.** The filter monkey-patches a module-level function, so the patch is process-wide the moment the filter loads; it is never scoped to the models you attach it to. A per-model install does not limit which models get `reasoning_content` forced, and it leaves the `excluded_model_ids` set dependent on whether an attached model happened to run — which is exactly when you don't want it empty. Enable it Global so `inlet` runs on every request and your exclusions are always live. Full reasoning in [Recommended setup](#-recommended-setup).
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
