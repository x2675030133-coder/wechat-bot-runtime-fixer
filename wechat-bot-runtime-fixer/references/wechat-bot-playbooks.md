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

## Bot Replies To Itself (Phantom Incoming Messages)

Symptoms:

- The user sent nothing, but the bot posts a full reply on its own.
- The bot answers the same sentence twice.
- Happens most after the bot sends several segments in quick succession (the chat view scrolls fast).

Inspect:

- The GUI-automation send driver: its "record sent text" hook, the echo-suppress timestamp/window, its sent-text cache, and its message-normalization helper.
- The OCR/screen message listener: its text-normalization helper, new-message detection, dedup fingerprinting, and dispatch.
- `bot.py`: the call that records a sent text after a text send, and any legacy send path.

Two distinct root causes (both produce "bot replies to itself"; diagnose before patching):

- **Scroll baseline drift.** File sends open a blunt echo-suppress window (within it, anything read back is judged self). Text sends historically relied only on a sent-text similarity cache (short TTL). That cache catches the bot's own bubble echo but *not* an old peer message that "revives" because fast scrolling moved the screen/OCR baseline. Across a multi-segment burst, early segments also age out of the cache TTL.
- **Punctuation-jitter re-read.** The same peer bubble gets read twice seconds apart with only punctuation differing (e.g. full-width vs half-width brackets), so it passes both overlap matching and fingerprint dedup as a "new" message and the bot answers twice. Tell: the bubble is correctly classified as peer (self-detection is not the problem — tuning that threshold does nothing).
- **UIA echo race.** UIA sees outgoing bubbles immediately. A broad quiet window can swallow real incoming messages, while arming a file marker after paste is too late to stop the outgoing image placeholder from being dispatched.

Fix pattern:

- Refresh the echo-suppress window on **every** text send (not just file sends), so each burst segment extends it. If both send paths converge on one "record sent text" point, fix it there once.
- Keep the listener's text-normalization stripping the *same* punctuation/bracket/quote set as the send driver's normalization. One aligned change closes both overlap matching and fingerprint dedup.
- The suppress window is deliberately blunter than similarity matching — that is the point; it stops drift phantoms the cache cannot.
- For UIA, use exact normalized sent-text matches instead of the OCR quiet window. Arm one outgoing file/image echo before clipboard paste and consume it only for the expected image placeholder type.
- In automatic receive mode, start one primary source; start notification/OCR fallbacks only when primary probing fails. Running all sources together recreates duplicate delivery.

Verify:

- Compile the send driver and the message listener.
- Run echo-filter, baseline-recovery, UIA-listener, and bubble-filter tests.
- Live triage: in the dispatch log, read the self-vs-peer signal. Peer classified as self was missed → tune the self-detection threshold. Correctly a peer bubble → check for same-sentence punctuation replay (normalization) or scroll drift (suppress window).
- Trade-off: lengthening the suppress window raises the risk of swallowing a *real* user message that lands inside it (it too is judged self). Do not lengthen it past the observed burst duration.

## Messages Silently Dropped By The Send Driver

Symptoms:

- A reply is generated but never reaches the chat app.
- Failures cluster when a clipboard manager, browser, or IME is active, or when the chat window is minimized / moved off-screen.
- The first segment sends, then every later segment reports that the main window is unavailable and is dropped.
- All upper-layer retries fail the same way rather than one flaky attempt.

Inspect:

- The GUI-automation send driver: its clipboard save/restore/set helpers, every simulated-click call site, focus helpers, and coordinate math derived from the window rect.
- The window manager and UIA listener: window discovery/activation, current-chat checks, target-chat search, and stale cache invalidation.
- The persistent log file: search for the send failure traceback (see the crash-logging playbook).

Two root causes:

- **Clipboard contention.** Opening the OS clipboard with no retry throws an access-denied error when another process briefly holds it; a single send then fails outright.
- **Automation fail-safe.** Click coordinates come from the window rect. A minimized / off-screen window yields garbage coords (screen corners, negatives); hitting a corner trips the automation library's fail-safe and crashes the whole send. The bad window state persists across all upper-layer retries, so every attempt dies identically.
- **Stale window/chat cache.** The driver trusts a cached main window handle or "already in this chat" marker after the window closed, reopened, or drifted. Retrying the same stale state drops every remaining reply segment.

Fix pattern:

- Route all clipboard helpers through a small retry-with-backoff wrapper. The lock usually frees in tens of ms, so the send self-heals internally without escalating to the upper retry loop.
- Never pass raw window-rect coords to the click primitive. Validate that the point is on a visible screen and not in a fail-safe corner, and wrap every click so it skips (returns failure) when out of bounds and catches the fail-safe exception. At critical focus points, return failure on invalid coords so the upper layer retries later (window may have recovered) instead of crashing.
- Before reusing the current-chat cache, ask the active listener whether the expected chat is still open. On mismatch or invalid handle, clear the cache, rediscover/activate the main window, reopen the target, and only then send.
- Propagate failure to the active send flow. Do not log success, advance/delete queued state, or keep dropping later segments after a send failure.
- Do **not** disable the global automation fail-safe (that removes the human emergency stop), do not switch to a different send path just to dodge this, and do not add another outer retry loop — the principle is "make one attempt less likely to fail," not "stack more retries."

Verify:

- Compile the send driver.
- Run send-resilience and UIA-listener tests (clipboard retry success / all-fail / self-heal; coordinate bounds; stale chat invalidation; focus/search failure).
- Test isolation gotcha: if other test files import the driver with the real automation library first, monkeypatch the library's click/size inside each test rather than relying on a self-installed stub's private attributes.

## Provider And Model Do Not Match

Symptoms:

- The API says a model is unsupported for the current endpoint.
- An image backend returns a deterministic 400 for parameters another backend accepts.
- The same 400 is retried several times with the same model, URL, key, and payload.
- Saving a masked key breaks only one model slot or silently reuses another provider's key.

Inspect:

- Config and editor: each slot's base URL, API-key field, model id, provider id, and fallback order.
- Runtime selection: retry classification and fallback behavior.
- Model catalog: discovery/edit metadata versus actual runtime slot wiring.
- Provider adapters: provider-specific request schema and normalized result.

Root cause:

- Model id, endpoint, credential, and provider schema were edited as independent strings even though they are one runtime tuple. Retrying an incompatible tuple cannot heal it.

Fix pattern:

- Keep base URL, key, model id, capabilities, and fallback order together per slot.
- Treat model-not-found, unsupported-model, endpoint, and invalid-parameter 400/404 responses as deterministic for that tuple. Move to a configured fallback or return a clear in-flow failure; do not retry the same tuple.
- Keep provider-specific parameters in the provider adapter and normalize only at the contract boundary.
- Resolve a masked key from the explicitly named saved field; never persist the mask or borrow another slot's secret.

Verify:

- Run model-management and provider-backend tests.
- Exercise one valid and one deliberately incompatible provider/model tuple; confirm the invalid tuple is attempted once and the fallback/result is visible.

## Deferred Background Work Is Lost Or Stuck

Symptoms:

- A memory or summary job is postponed when a new message arrives, but never runs again.
- The same work is queued multiple times.
- Restart leaves an item forever in `processing`.
- A failed handler deletes its work or retries with no error/attempt record.

Inspect:

- The producer and consumer: enqueue point, claim point, success/failure transitions.
- The durable queue implementation.
- Any in-memory sets/lists that claim to represent retryable work.

Root cause:

- Retryable work was represented as ephemeral process state, or removed before success was known. Interruptions and restarts then look like successful completion.

Fix pattern:

- Use the smallest durable queue already available (SQLite is enough): dedupe on enqueue, atomically claim the oldest pending/failed item, delete only after success, and record a bounded error plus attempt count on failure.
- On startup, recover stale `processing` items to `pending`.
- Treat "new message arrived; defer" as a retryable failure/status transition, not a terminal exception that loses the candidate.

Verify:

- Check dedupe, success deletion, failure retry, exception recording, and restart recovery.

## Generated Images Look "Too AI"

Symptoms:

- Selfies come out uncanny, plastic, over-rendered, or just "off."
- Tuning style words or the negative prompt barely helps.
- The character's face drifts even though a reference photo is configured.

Inspect:

- `bot.py`: the image-generation entry — what it passes as the persona/character summary (does it load the full chat character prompt?).
- `config_editor.py`: the test-image endpoint — does it load the full character prompt too?
- `image_generation.py`: prompt builder, persona summarizer, workflow-request builder.
- `config.py`: a dedicated image-appearance setting, the default style, and the negative prompt.

Root cause (recurs easily — pin it down):

- The **whole chat behavior protocol** was being fed into the image prompt as persona. The character prompt file is a large chat protocol (behavior rules, state machine, output samples). A persona summarizer that keeps only the first few hundred chars keeps exactly the "how to type" rules and prepends them to the image prompt, drowning the appearance/scene description. The character's *looks* are already locked by the reference photo + workflow, so the image prompt needs no behavior protocol at all.

Fix pattern:

- Add a dedicated single-line image-appearance setting (visual anchor only — "what they look like"; empty = rely on reference photo + workflow).
- Replace the persona at every image-prompt assembly point (scene direction, workflow request, prompt builder) with that appearance setting. Leave the full character-prompt loaders intact — they still feed the chat main path.
- Anti-AI-look hygiene in the prompt builder and the style/negative constants: open with "ordinary person's casual phone snapshot, not a professional/AI render"; add realism cues (pores/minor blemishes, real ambient light with shadows, imperfect framing, restrained color + slight grain); close with hard constraints against AI tells (waxy plastic skin, beauty-filter, over-saturated HDR, studio CGI light, doll symmetry, over-sharpening).
- If the image backend has no separate negative parameter, negatives take effect only as an `Avoid:` segment appended into the prompt text.

Verify:

- Compile the touched Python files.
- Run the image-prompt regression tests (default style carries anti-AI anchors; the appearance string reaches persona; the final end-to-end prompt contains no chat-protocol junk).
- Text-only changes: the actual anti-AI effect needs one live generation to confirm. Use the config page prompt preview to inspect assembly, then compare on a real device.

## Bot Died With No Recorded Cause

Symptoms:

- A status check warns that the heartbeat is recent but the process PID no longer exists — the process is gone but the death cause is unknown.
- The console window was closed (logs lost) or only network-push logging existed (dies with the process).

Inspect:

- `bot.py`: the logger config block — is there a file handler? Are there main-thread and worker-thread uncaught-exception hooks?
- The log file, if present: search for CRITICAL or traceback markers.

Root cause:

- No persistent file handler, so crash tracebacks never hit disk. Worse, an uncaught exception goes to stderr and bypasses logging entirely — even a file handler alone would miss it.

Fix pattern:

- Add a rotating file handler (bounded size × a few backups), UTF-8, auto-creating its log directory.
- Strip ANSI color codes before writing to the file, or colored console output lands as escape-sequence garbage.
- Install both a main-thread and a worker-thread uncaught-exception hook to log crashes with full traceback at CRITICAL; let keyboard-interrupt through.
- File-log init failure should warn, not block startup (it is an aid, not a dependency).

Verify:

- Compile `bot.py`.
- Confirm non-ASCII text is intact, ANSI is fully stripped, and a forced exception in both a main-thread and a worker-thread path lands a full traceback in the log file.
