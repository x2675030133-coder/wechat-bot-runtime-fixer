# Chat Bot Runtime Fixer

A portable skill pack for diagnosing and fixing Python chat bot runtime issues around media delivery, voice replies, config editors, and user-facing verification.

It includes a Codex-compatible `SKILL.md`, plus a README, playbooks, and a static diagnostic script that other AI coding assistants can also use as reference material.

This pack was distilled from real debugging patterns: placeholder messages that never become images, voice previews that bypass generation toggles, per-user voice settings that drift away from chat routing, and send flows that look correct internally but fail in the final user-facing result.

## What It Helps Fix

- Image generation that sends placeholders as plain text instead of a real file.
- Generated images or audio files that never reach the chat app.
- Voice mappings that should follow users but appear as fixed role rows.
- Uploaded/custom voice generation that ignores an enable/disable toggle.
- Config editor defaults, preview routes, or save logic that diverge from runtime behavior.
- Queue and send-flow bugs where messages can disappear after exceptions.

## What's Included

```text
wechat-bot-runtime-fixer/
├─ SKILL.md
├─ agents/
│  └─ openai.yaml
├─ references/
│  └─ wechat-bot-playbooks.md
└─ scripts/
   └─ diagnose_wechat_bot.py
```

## Installation

Copy the skill folder into your Codex skills directory:

```bash
mkdir -p ~/.codex/skills
cp -r wechat-bot-runtime-fixer ~/.codex/skills/
```

For a project-local install, copy it into your repo's skill directory:

```bash
mkdir -p .agents/skills
cp -r wechat-bot-runtime-fixer .agents/skills/
```

On Windows PowerShell:

```powershell
New-Item -ItemType Directory -Force -Path "$env:USERPROFILE\.codex\skills"
Copy-Item -Recurse -Force .\wechat-bot-runtime-fixer "$env:USERPROFILE\.codex\skills\"
```

## Usage

Ask your assistant to use the skill:

```text
Use $wechat-bot-runtime-fixer to diagnose why my chat bot only sends [拍照] instead of an image.
```

The same prompt pattern works well in Codex, ChatGPT, and other coding assistants that can read repository files or follow a prompt-based skill pack.

Or run the bundled static diagnostic script from your bot repository:

```bash
python .agents/skills/wechat-bot-runtime-fixer/scripts/diagnose_wechat_bot.py --repo .
```

If installed globally:

```bash
python ~/.codex/skills/wechat-bot-runtime-fixer/scripts/diagnose_wechat_bot.py --repo /path/to/your/bot
```

The diagnostic script does not import your bot modules. It reads files statically to avoid triggering local side effects, secrets, or machine-specific startup code.

## Recommended Workflow

1. Start from the visible user-facing failure.
2. Run `diagnose_wechat_bot.py` to get a triage map.
3. Inspect the files named by the diagnostic output.
4. Fix every coupled layer in one pass.
5. Verify the real user-facing result, not just logs or prompt output.

## Example Prompts

```text
Use $wechat-bot-runtime-fixer to fix image generation placeholders being sent as text.
```

```text
Use $wechat-bot-runtime-fixer to make uploaded voice preview respect the generation toggle.
```

```text
Use $wechat-bot-runtime-fixer to align per-user voice mapping with LISTEN_LIST.
```

## Notes

- The skill is intentionally conservative: it prefers small fixes and explicit verification.
- The diagnostic script is read-only.
- No private keys, tokens, user names, or machine paths are included.
- Licensed under MIT. See [`LICENSE`](LICENSE).
- The Codex `SKILL.md` is the only Codex-specific file; the rest of the pack is designed to be useful in other AI coding tools too.

---

# 聊天机器人运行时修复包

这是一个可复用的技能包，既能给 Codex 用，也适合其他 AI 编程助手参考。它用来诊断和修复 Python 聊天机器人里的运行时问题，重点覆盖图片发送、语音回复、配置页、预览接口，以及最终用户真正看到的结果。

这个包来自真实项目排错经验：例如占位符没有变成图片、上传音色预览绕过开关、按用户配置的语音映射变成固定角色列表、内部日志看似成功但最终没有真正发出文件等。

## 能解决什么

- 图片生成只发送占位符文字，而没有真正生成文件。
- 已生成的图片或音频没有真正发到聊天应用。
- 语音配置应该跟随用户列表，但界面看起来像固定角色配置。
- 上传音色/自定义音色没有遵守生成开关。
- 配置页默认值、预览接口、保存逻辑和运行时行为不一致。
- 队列或发送流程异常时，消息可能丢失。

## 包含内容

```text
wechat-bot-runtime-fixer/
├─ SKILL.md
├─ agents/
│  └─ openai.yaml
├─ references/
│  └─ wechat-bot-playbooks.md
└─ scripts/
   └─ diagnose_wechat_bot.py
```

## 安装方法

复制 skill 文件夹到 Codex skills 目录：

```bash
mkdir -p ~/.codex/skills
cp -r wechat-bot-runtime-fixer ~/.codex/skills/
```

如果想放在项目本地：

```bash
mkdir -p .agents/skills
cp -r wechat-bot-runtime-fixer .agents/skills/
```

Windows PowerShell：

```powershell
New-Item -ItemType Directory -Force -Path "$env:USERPROFILE\.codex\skills"
Copy-Item -Recurse -Force .\wechat-bot-runtime-fixer "$env:USERPROFILE\.codex\skills\"
```

## 使用方法

让你的助手使用这个 skill：

```text
Use $wechat-bot-runtime-fixer to diagnose why my chat bot only sends [拍照] instead of an image.
```

这个写法对 Codex、ChatGPT，以及其他能读取仓库文件或跟随技能说明的编程助手都比较通用。

也可以在机器人项目根目录运行静态诊断脚本：

```bash
python .agents/skills/wechat-bot-runtime-fixer/scripts/diagnose_wechat_bot.py --repo .
```

如果是全局安装：

```bash
python ~/.codex/skills/wechat-bot-runtime-fixer/scripts/diagnose_wechat_bot.py --repo /path/to/your/bot
```

诊断脚本不会 import 你的机器人代码，只会静态读取文件，避免触发本机副作用、私密配置或启动逻辑。

## 推荐流程

1. 先从用户能看到的问题开始。
2. 运行 `diagnose_wechat_bot.py` 得到排查地图。
3. 按诊断结果检查对应文件。
4. 对耦合路径一次性修完整。
5. 验证聊天应用里真正看到的结果，而不是只看日志或提示词输出。

## 示例提问

```text
Use $wechat-bot-runtime-fixer to fix image generation placeholders being sent as text.
```

```text
Use $wechat-bot-runtime-fixer to make uploaded voice preview respect the generation toggle.
```

```text
Use $wechat-bot-runtime-fixer to align per-user voice mapping with LISTEN_LIST.
```

## 说明

- 这个 skill 默认保守修复：小改动、强验证。
- 诊断脚本是只读的。
- 不包含私人 key、token、用户名、本机路径或项目专属名称。
