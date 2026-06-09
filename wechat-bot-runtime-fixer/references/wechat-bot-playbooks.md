# Chat Bot Playbooks

Use these playbooks after reading the live code. Function names and line numbers drift; behavior rules matter more than exact anchors. WeChat names appear here as reference examples, but the patterns apply to other chat apps with the same shape of bug.

## Image Placeholder Sent As Text

Symptoms:

- User says `拍照`, `拍张照`, or `发张自拍`, but the chat app receives `[拍照]`, `[照片]`, or `【照片】(...)`.
- Logs show an image intent, but the send path emits text instead of a file.

Inspect:

- `config.py`: image trigger keywords
- `config_editor.py`: default trigger metadata and save parsing for image triggers
- `bot.py`: user-message routing, `send_reply()`, placeholder/action parsing, and the app's send-file call
- `image_generation.py`: generation entrypoints and fallback behavior

Fix pattern:

- Keep trigger defaults in sync between config and editor.
- Normalize image requests before generation. Include direct Chinese triggers such as `拍照`, `拍张照`, `拍个照`, `发张照片`, and `发张自拍` when appropriate.
- Treat `[照片]`, `[拍照]`, `【照片】(...)`, and `【拍照】` as action protocols, not final text.
- Convert the action into generated image file delivery through the app's send-file call.
- If no description exists, use a default selfie-style prompt instead of sending the raw placeholder.
- Send fallback notices inside the active send flow so send locks/state do not conflict.

Verify:

- Compile the touched Python files.
- Exercise representative image prompts in the closest available harness.
- Confirm the end result is an actual image file sent to the chat app or a clear in-flow fallback.

## Voice Mapping Looks Fixed Or Wrong User Gets Voice

Symptoms:

- Voice config page looks like fixed roles rather than the app's user list.
- Per-user voice setting does not match the chat target.
- Runtime picks role/prompt fallback before nickname/remark mapping.

Inspect:

- `config.py`: user list, per-user voice mappings, custom voice mappings
- `config_editor.py`: voice target option builder, form save logic, editor template context
- `templates/config_editor.html`: rendered voice rows
- `voice_profile.py`: `resolve_voice_profile(...)`, catalog helpers
- `bot.py`: caller that resolves voice for the current user

Fix pattern:

- Build voice target rows from the app's user list, one row per nickname/remark.
- Keep nickname first in the UI, with prompt/role as secondary context.
- Preserve `resolve_voice_profile(..., user_key=...)` semantics and ensure the runtime caller passes `user_key`.
- Reuse built-in voice catalog and validation helpers; do not rebuild separate voice catalogs.
- Do not reuse image-generation target lists or prompt-deduped helper lists for voice mapping.

Verify:

- Compile the touched Python files.
- Open the config editor and confirm rows mirror the app's user list.
- Save a per-user voice mapping and verify the runtime lookup uses the nickname/remark before role fallback.

## Uploaded Voice Generation Toggle Ignored

Symptoms:

- Uploaded voice preview synthesizes new speech even when generation is disabled.
- Runtime sends generated speech from uploaded voice while the enable/disable toggle is false.
- Local synthesis services are called in the disabled state.

Inspect:

- `config.py`: uploaded-voice generation toggle and cache/service settings
- `config_editor.py`: preview endpoint and web preview behavior
- `voice_profile.py`: uploaded/custom voice synthesis
- `bot.py`: runtime voice reply generation and send path
- `wechat_voice_sender.py`: audio send behavior if touched

Fix pattern:

- Gate every path that synthesizes new speech from an uploaded voice with the toggle.
- Check both runtime sending and web preview routes.
- When disabled, uploaded voices should remain library/preview/binding assets. Preview should play original uploaded audio when possible or clearly report that generation is disabled.
- When enabled, cache-first reuse and local synthesis can be valid.

Verify:

- Disabled state: preview/runtime must not call speech synthesis endpoints.
- Enabled state: expected generation/cache path still works.
- Compile touched Python files and test the browser preview route when available.

## Config Editor Diverges From Runtime

Symptoms:

- A saved setting does not match `config.py`.
- The editor shows defaults that runtime does not use.
- UI shape suggests a different model than bot routing.

Inspect:

- `config.py`: canonical defaults
- `config_editor.py`: default map, form parsing, API serialization, route handlers
- `templates/config_editor.html`: actual controls and row shape
- Runtime caller in `bot.py` or `voice_profile.py`

Fix pattern:

- Update defaults and editor metadata together.
- Keep parsing structured; avoid ad hoc string parsing when the editor already has list/dict helpers.
- Preserve local secrets and user config values. Do not broaden cleanup.
- Browser-check rendered controls after compile success.

Verify:

- Compile the touched Python files.
- Save through the editor if possible, reload config, and verify runtime reads the saved value.

## Message Queue Or Send Flow Can Lose Work

Symptoms:

- Messages disappear after an exception.
- Fallback sends race with existing send locks.
- A queue entry is removed before the send path succeeds.

Inspect:

- `bot.py`: queue processing, send lock/state, `check_inactive_users()`, `process_user_messages()`, and fallback send helpers

Fix pattern:

- Do not remove queue state before success is known.
- Prefer explicit mark-processing and finish-processing phases.
- Keep fallback notices in the same send flow where possible.
- Avoid broad rewrites of long routines; patch the smallest state transition that preserves queued messages.

Verify:

- Compile `bot.py`.
- Exercise success and exception paths in the smallest available harness or by carefully reading state transitions.
