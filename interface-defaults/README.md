# Interface Defaults

Set the **Settings > Interface** defaults for your whole instance, configured entirely from this function's Valves in the admin panel. No custom UI, no monkey-patching, no startup hooks — it rides Open WebUI's native events system.

## What it does

- **New users are seeded automatically.** The function subscribes to the `user.created` event (which fires for signup, OAuth, **and** SCIM), so every newly created account inherits the interface settings you configure here.
- **Apply to all existing users** (one-shot button). Tick `apply_to_all_existing_users` + Save to push the configured settings to everyone who already exists. Normally only needed once, right after installing.
- **Full factory reset** (one-shot button). Tick `reset_all_users_to_factory` + Save to clear every user's interface overrides (reverting everyone to Open WebUI's built-in defaults) **and** reset this function's own settings back to their defaults.

Both buttons run in the background and untick themselves once done.

## How it works

Open WebUI's events system dispatches in-process to any `Event` function that defines an `event` handler. This plugin:

- on `user.created` → writes the configured interface settings into the new user's `settings.ui`.
- on `function.valves_updated` (its own) → checks the trigger toggles and runs the bulk apply / reset, then clears the trigger via the model layer (which doesn't re-publish, so there's no loop).

The settings themselves are plain Valves: booleans render as toggles, `chatDirection` as a dropdown, `textScale` as a number. Defaults match Open WebUI's factory values, so a fresh install behaves identically until you change something.

## Requirements

- An Open WebUI build with the **events system** (the `Event` function type + `user.created` / `function.valves_updated` events). Available on `dev`; ships in the corresponding release.
- Valve descriptions render as markdown on builds that include the markdown valve-description change (also on `dev`); on older builds they show as plain text.

## Install

Admin Panel > Functions > **+** (Import/Create) > paste `event.py`, save, and **enable** it. Configure the defaults in its Valves. That's it.

## Notes

- **Apply vs reset asymmetry:** apply keeps your configured settings (so new users keep getting them); reset wipes both the users and the config (it's a true factory reset).
- **Cosmetic:** after a trigger runs, the background task unticks it in the DB, but an already-open admin form may still *show* it ticked until you refresh.
- Existing users are never touched except by the two explicit buttons.
