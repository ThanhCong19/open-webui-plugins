"""
title: Interface Defaults
author: Classic298
version: 1.0.1
required_open_webui_version: 0.10.0
description: Manage Settings > Interface defaults instance-wide from this function's Valves. New users are seeded automatically (subscribes to user.created, which fires for signup, OAuth, and SCIM). Two trigger toggles act as one-shot buttons: "Apply to all existing users" pushes the settings above to everyone (normally only needed once, right after install), and "Reset all users to factory" does a full reset — clears every user's overrides AND resets this config back to defaults. Tick a trigger and Save; it runs in the background and unticks itself. Booleans render as toggles, direction as a dropdown, text scale as a number. No custom UI, no monkey-patching, no startup hooks. Defaults below match Open WebUI's factory values.
"""

import asyncio
import logging
from typing import Literal, Optional

from pydantic import BaseModel, Field

log = logging.getLogger(__name__)

# Valve fields that are NOT interface settings (excluded when building ui).
_TRIGGERS = ('apply_to_all_existing_users', 'reset_all_users_to_factory')


class Event:
    class Valves(BaseModel):
        # ── UI ──────────────────────────────────────────────────────────────
        textScale: float = Field(default=1.0, description='UI scale (1.0 - 1.5)')
        highContrastMode: bool = Field(default=False, description='High contrast mode')
        showChatTitleInTab: bool = Field(default=True, description='Display chat title in browser tab')
        notificationSound: bool = Field(default=True, description='Notification sound')
        notificationSoundAlways: bool = Field(default=False, description='Always play notification sound')
        userLocation: bool = Field(default=False, description='Allow access to user location')
        hapticFeedback: bool = Field(default=False, description='Haptic feedback (Android)')
        copyFormatted: bool = Field(default=False, description='Copy formatted text')
        showUpdateToast: bool = Field(default=True, description='Toast notifications for new updates (admin)')
        showChangelog: bool = Field(default=True, description="Show \"What's New\" modal on login (admin)")

        # ── Chat ────────────────────────────────────────────────────────────
        enableMessageQueue: bool = Field(default=True, description='Enable message queue')
        chatDirection: Literal['auto', 'LTR', 'RTL'] = Field(default='auto', description='Chat text direction')
        landingPageMode: Literal['', 'chat'] = Field(default='', description="Landing page: '' = default, 'chat' = chat")
        chatBubble: bool = Field(default=True, description='Chat bubble UI')
        showUsername: bool = Field(default=False, description='Display username instead of You (bubble UI off)')
        widescreenMode: bool = Field(default=False, description='Widescreen mode')
        temporaryChatByDefault: bool = Field(default=False, description='New chats are temporary by default')
        chatFadeStreamingText: bool = Field(default=True, description='Fade effect for streaming text')
        renderMarkdownInUserMessages: bool = Field(default=True, description='Render markdown in user messages')
        renderMarkdownInAssistantMessages: bool = Field(default=True, description='Render markdown in assistant messages')
        titleAutoGenerate: bool = Field(default=True, description='Title auto-generation')
        autoFollowUps: bool = Field(default=True, description='Follow-up auto-generation')
        autoTags: bool = Field(default=True, description='Chat tags auto-generation')
        responseAutoCopy: bool = Field(default=False, description='Auto-copy response to clipboard')
        insertSuggestionPrompt: bool = Field(default=False, description='Insert suggestion prompt to input')
        keepFollowUpPrompts: bool = Field(default=False, description='Keep follow-up prompts in chat')
        insertFollowUpPrompt: bool = Field(default=False, description='Insert follow-up prompt to input')
        regenerateMenu: bool = Field(default=True, description='Regenerate menu')
        collapseCodeBlocks: bool = Field(default=False, description='Always collapse code blocks')
        expandDetails: bool = Field(default=False, description='Always expand details')
        renderMarkdownInPreviews: bool = Field(default=True, description='Render markdown in previews')
        displayMultiModelResponsesInTabs: bool = Field(default=False, description='Display multi-model responses in tabs')
        scrollOnBranchChange: bool = Field(default=True, description='Scroll on branch change')
        showFilesOnTerminalSelect: bool = Field(default=True, description='Show files on terminal select')
        stylizedPdfExport: bool = Field(default=True, description='Stylized PDF export')
        showFloatingActionButtons: bool = Field(default=True, description='Floating quick actions')
        splitLargeChunks: bool = Field(default=False, description='Split large chunks')

        # ── Input ───────────────────────────────────────────────────────────
        ctrlEnterToSend: bool = Field(default=False, description='Ctrl+Enter to send (off = Enter to send)')
        richTextInput: bool = Field(default=True, description='Rich text input for chat')
        promptAutocomplete: bool = Field(default=False, description='Prompt autocompletion')
        showFormattingToolbar: bool = Field(default=False, description='Show formatting toolbar (rich text on)')
        insertPromptAsRichText: bool = Field(default=False, description='Insert prompt as rich text (rich text on)')
        largeTextAsFile: bool = Field(default=False, description='Paste large text as a file')

        # ── Artifacts ───────────────────────────────────────────────────────
        detectArtifacts: bool = Field(default=True, description='Detect artifacts automatically')
        iframeSandboxAllowSameOrigin: bool = Field(default=False, description='iframe sandbox allow same origin')
        iframeSandboxAllowForms: bool = Field(default=False, description='iframe sandbox allow forms')

        # ── Voice ───────────────────────────────────────────────────────────
        voiceInterruption: bool = Field(default=False, description='Allow voice interruption in call')
        showEmojiInCall: bool = Field(default=False, description='Display emoji in call')

        # ── File ────────────────────────────────────────────────────────────
        imageCompression: bool = Field(default=False, description='Compress images before upload')
        imageCompressionInChannels: bool = Field(default=True, description='Compress images in channels (compression on)')
        imageCompressionWidth: str = Field(default='', description='Max image width in px (blank = no limit)')
        imageCompressionHeight: str = Field(default='', description='Max image height in px (blank = no limit)')

        # Reassembled into their real ui shape on apply:
        webSearchAlways: bool = Field(default=False, description="Enable web search by default (maps to webSearch='always')")

        # --- one-shot trigger "buttons" (tick + Save; they untick themselves) ---
        apply_to_all_existing_users: bool = Field(
            default=False,
            description='**Button — one-time, post-install.** Tick + Save to push every setting above to **all existing users**. You normally only need this once, right after installing: from then on **new users are seeded automatically** on signup. Runs in the background and unticks itself (may take a minute on large instances).',
        )
        reset_all_users_to_factory: bool = Field(
            default=False,
            description="**Button — full factory reset.** Tick + Save to clear interface overrides for **every user** (reverting everyone to Open WebUI's built-in defaults) **and** reset all settings above back to their defaults. Unticks itself.",
        )

    def __init__(self):
        self.valves = self.Valves()

    # ── helpers ──────────────────────────────────────────────────────────────

    def _ui_from_valves(self) -> dict:
        """The interface ui dict to write into a user, from the configured valves."""
        ui = self.valves.model_dump()
        for key in _TRIGGERS:
            ui.pop(key, None)
        ui['title'] = {'auto': ui.pop('titleAutoGenerate', True)}
        ui['webSearch'] = 'always' if ui.pop('webSearchAlways', False) else None
        ui['imageCompressionSize'] = {'width': ui.pop('imageCompressionWidth', ''), 'height': ui.pop('imageCompressionHeight', '')}
        return ui

    async def _all_users(self):
        from open_webui.models.users import Users

        res = await Users.get_users()
        return (res.get('users', []) if isinstance(res, dict) else res) or []

    async def _seed_user(self, user_id: str, ui: dict):
        from open_webui.models.users import Users

        user = await Users.get_user_by_id(user_id)
        if not user:
            return
        current = dict((user.settings.model_dump() if user.settings else {}) or {})
        merged = dict(current.get('ui') or {})
        merged.update(ui)
        await Users.update_user_settings_by_id(user_id, {'ui': merged})

    async def _apply_to_all(self, ui: dict):
        users = await self._all_users()
        for user in users:
            try:
                await self._seed_user(user.id, ui)
            except Exception:
                log.exception('interface-defaults: apply failed for %s', user.id)
        log.info('interface-defaults: applied defaults to %d existing user(s)', len(users))

    async def _reset_all(self):
        from open_webui.models.users import Users

        users = await self._all_users()
        for user in users:
            try:
                await Users.update_user_settings_by_id(user.id, {'ui': {}})
            except Exception:
                log.exception('interface-defaults: reset failed for %s', user.id)
        log.info('interface-defaults: reset %d user(s) to factory defaults', len(users))

    async def _clear_triggers(self, function_id: str):
        """Untick the trigger toggles in the DB (keeps the configured settings).
        The model write does not publish the event, so there is no re-fire loop."""
        from open_webui.models.functions import Functions

        valves = await Functions.get_function_valves_by_id(function_id) or {}
        for key in _TRIGGERS:
            valves[key] = False
        await Functions.update_function_valves_by_id(function_id, valves)

    async def _reset_valves(self, function_id: str):
        """Restore this function's valves to their pydantic defaults (factory config)."""
        from open_webui.models.functions import Functions

        await Functions.update_function_valves_by_id(function_id, self.Valves().model_dump())

    # ── event entry point ────────────────────────────────────────────────────

    async def event(self, event: Optional[dict] = None, __event_name__: str = '', __id__: str = '', **kwargs):
        payload = event or {}

        # 1) Seed every brand-new user (signup / oauth / scim).
        if __event_name__ == 'user.created':
            user_id = (payload.get('subject') or {}).get('id')
            if user_id:
                await self._seed_user(user_id, self._ui_from_valves())
            return

        # 2) Trigger buttons: fire when THIS function's valves are saved.
        if __event_name__ == 'function.valves_updated':
            if (payload.get('subject') or {}).get('id') != __id__:
                return
            do_reset = bool(self.valves.reset_all_users_to_factory)
            do_apply = bool(self.valves.apply_to_all_existing_users)
            if not (do_reset or do_apply):
                return
            # Bulk op runs in the background so the admin's Save returns immediately.
            if do_reset:
                # Full factory reset: restore this config to defaults AND clear every user.
                await self._reset_valves(__id__)
                asyncio.create_task(self._reset_all())
            elif do_apply:
                # Snapshot the configured ui first, then untick only the trigger so the
                # configured settings are kept (new users keep getting seeded with them).
                ui = self._ui_from_valves()
                await self._clear_triggers(__id__)
                asyncio.create_task(self._apply_to_all(ui))
