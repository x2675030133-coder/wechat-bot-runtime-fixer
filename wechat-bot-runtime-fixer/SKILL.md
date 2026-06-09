---
name: wechat-bot-runtime-fixer
description: Diagnose and fix Python WeChat bot runtime issues. Use when working in a repo with bot.py, config.py, config_editor.py, voice_profile.py, image_generation.py, LISTEN_LIST, wx.SendFiles, uploaded voice generation, config editor previews, WeChat message sending, or symptoms like only sending [photo] placeholders, voice preview bypassing toggles, per-user voice mappings looking fixed, or generated media not reaching WeChat.
---

# WeChat Bot Runtime Fixer

Use this skill to turn WeChat bot complaints into working user-facing behavior. The goal is not a clean log line; the goal is the actual sent text, image, audio, preview, or saved config that the user sees.

## First Move

Run the diagnostic script when the repo is available:

```bash
python .agents/skills/wechat-bot-runtime-fixer/scripts/diagnose_wechat_bot.py --repo .
```

Use the output as a triage map, not as final truth. Then inspect the named files directly with `rg` and file reads.

## Workflow

1. Start from the visible symptom: what did WeChat, the config page, or the preview endpoint actually do?
2. Trace ingress: user message, model placeholder, config form/API, web preview, timer, or automation probe.
3. Trace delivery: `wx.SendFiles()`, text send, generated audio file, generated image file, config save, or browser preview response.
4. Fix all coupled layers in one pass. Trigger words plus placeholder parsing plus file send are one bug class; runtime synthesis plus web preview toggle behavior is another.
5. Verify the user-facing surface when available. If WeChat, browser, or local synthesis services are unavailable, report the exact verification boundary and the lower-level checks that passed.

## Issue Playbooks

Load `references/wechat-bot-playbooks.md` when the task involves one of these areas:

- Image generation sends `[photo]`, `[拍照]`, `[照片]`, or `【照片】(...)` as text.
- Voice mapping must follow WeChat users rather than role/prompt-deduped rows.
- Uploaded/custom voice generation or preview ignores `VOICE_REPLY_UPLOADED_GENERATION_ENABLED`.
- Config editor defaults, form parsing, or preview routes diverge from runtime behavior.
- Queue/send-flow errors risk losing messages or sending fallback notices outside the active send path.

## Non-Negotiables

- Treat `LISTEN_LIST` as the per-chat source of truth for this bot style of routing.
- Do not replace a real WeChat outcome with placeholder text, fake image tags, or audio path strings.
- Do not edit generated media, uploaded voices, memory folders, chat contexts, or user config broadly unless the user explicitly asks.
- Prefer small code changes in existing helpers over new abstractions unless the bug spans repeated logic.
- Explain root cause before the fix when the user asks why a visible behavior broke.

## Verification Menu

Use the smallest set that reaches the changed surface:

```bash
python -m py_compile bot.py config.py config_editor.py voice_profile.py image_generation.py wechat_voice_sender.py
python -m pytest test_chat_response_utils.py test_config_editor_api_key_masking.py test_image_generation_fallback.py test_voice_bubble_probe.py
python .agents/skills/wechat-bot-runtime-fixer/scripts/diagnose_wechat_bot.py --repo .
```

For UI/config work, also open the config editor in a browser and verify render shape, save behavior, and preview behavior.

For media send work, test representative examples in the closest available harness. Good image examples include `拍照`, `拍张照`, `发张自拍`, `[拍照]`, `[照片]`, and `【照片】在图书馆随手拍的自拍`.
