# 🎛️ Interface Defaults

Set the **Settings → Interface** defaults for your entire instance from one function's Valves. New users are seeded automatically, and two one-shot buttons let you apply the defaults to everyone or factory-reset the whole instance.

> [!IMPORTANT]
> **Requires Open WebUI `0.10.0` or newer.** This is an `Event` function and depends on the native events system (`user.created` / `function.valves_updated`). It will not load on older versions.

> [!TIP]
> **🚀 [Jump to Setup](#setup)** — paste, enable, configure. Under a minute, no restart.

## ✨ Features

- **Automatic seeding of new users** — every account created via signup, OAuth, or SCIM inherits your configured interface settings.
- **Apply to all existing users** — a one-shot button to push the defaults to everyone already on the instance.
- **Full factory reset** — a one-shot button that clears every user's interface overrides *and* resets this function's config back to defaults.
- **Native Valves UI** — booleans render as toggles, direction as a dropdown, text scale as a number. No custom UI.
- Defaults match Open WebUI's own factory values, so nothing changes until you change it.

## ✅ How it works

Open WebUI dispatches events in-process to any `Event` function that defines an `event` handler. This plugin reacts to two:

- `user.created` → writes the configured interface settings into the new user's `settings.ui`.
- `function.valves_updated` (its own) → runs the apply / reset when you tick a trigger toggle and **Save**, then unticks it via the model layer (no re-publish, so there is no loop).

Both bulk operations run in the background, so saving returns immediately even on large instances.

> [!NOTE]
> **Apply vs reset.** *Apply* keeps your configured settings (so new users keep getting them). *Reset* is a true factory reset — it wipes both the users' overrides and this function's own config.

## Components

| File | Type | Install location |
|------|------|-----------------|
| `event.py` | Event | Admin Panel → Functions |

## Setup

1. Copy the contents of `event.py`, or click **Get** on the Community page.
2. In Open WebUI, go to **Admin Panel → Functions → +** (Import/Create).
3. Paste the code and click **Save**.
4. **Enable** the function.
5. Open its **Valves** and set your interface defaults.
6. *(First install only)* Tick **Apply to all existing users** and **Save** to seed everyone already on the instance.

## Usage

- **New users** — nothing to do; they're seeded automatically on registration.
- **Change a default later** — edit the Valves, then either leave it (new users get the change automatically) or tick **Apply to all existing users** + **Save** to push it to everyone.
- **Start over** — tick **Reset all users to factory** + **Save**.

> [!WARNING]
> The two buttons act on **every** user. *Apply* overwrites the configured keys for all existing users; *Reset* clears all interface overrides instance-wide. Both untick themselves once the background job finishes — an already-open form may show the toggle as still ticked until you refresh.
