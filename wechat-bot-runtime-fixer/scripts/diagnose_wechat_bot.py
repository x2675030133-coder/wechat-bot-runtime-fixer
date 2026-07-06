#!/usr/bin/env python3
"""Static chat bot repo diagnostics.

This script intentionally does not import project modules. Bot config files can
contain local secrets, side effects, or machine-specific paths, so diagnostics
work by reading text and checking known problem surfaces.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path


CORE_FILES = [
    "bot.py",
    "config.py",
    "config_editor.py",
    "voice_profile.py",
    "image_generation.py",
]

IMAGE_TRIGGERS = ["拍照", "拍张照", "拍个照", "发张照片", "发张自拍"]
IMAGE_PLACEHOLDERS = ["[拍照]", "[照片]", "【拍照】", "【照片】"]
VOICE_TOGGLE = "VOICE_REPLY_UPLOADED_GENERATION_ENABLED"


@dataclass
class Finding:
    status: str
    area: str
    message: str
    evidence: str = ""

    def as_dict(self) -> dict[str, str]:
        return {
            "status": self.status,
            "area": self.area,
            "message": self.message,
            "evidence": self.evidence,
        }


def read_text(path: Path) -> str:
    for encoding in ("utf-8-sig", "utf-8", "gbk"):
        try:
            return path.read_text(encoding=encoding)
        except UnicodeDecodeError:
            continue
    return path.read_text(errors="replace")


def has_all(text: str, needles: list[str]) -> tuple[bool, list[str]]:
    missing = [needle for needle in needles if needle not in text]
    return not missing, missing


def grep_context(text: str, pattern: str) -> str:
    match = re.search(pattern, text, re.MULTILINE)
    if not match:
        return ""
    line_no = text[: match.start()].count("\n") + 1
    line = text.splitlines()[line_no - 1].strip()
    return f"line {line_no}: {line[:180]}"


# config.py is commonly read line-by-line with a regex like `^KEY\s*=\s*(.+)$` by BOTH the
# config editor's parser and the bot's dynamic-config reader; `.` does not span lines. These
# two static checks catch the most common, silently-broken config bug class in this bot shape.
_TOP_LEVEL_ASSIGN = re.compile(r"^([A-Za-z_]\w*)\s*=")
# A list/dict whose opening bracket is the last real content on the line => its value spans
# multiple lines, so the parser reads only `[` or `{` and the real value is lost.
_MULTILINE_OPENER = re.compile(r"^([A-Za-z_]\w*)\s*=\s*([\[{])\s*(#.*)?$")


def check_config_parsing(config: str) -> list[Finding]:
    findings: list[Finding] = []
    if not config:
        return findings

    lines = config.splitlines()

    # 1) Multi-line list/dict values (top-level / column 0 only — that is where config
    #    settings live and what the line-based parser actually keys on).
    multiline_hits: list[str] = []
    for idx, line in enumerate(lines, start=1):
        m = _MULTILINE_OPENER.match(line)
        if m:
            multiline_hits.append(f"line {idx}: {m.group(1)} = {m.group(2)} ...")
    if multiline_hits:
        findings.append(Finding(
            "WARN", "config-parse",
            "Multi-line list/dict in config.py will be misread by line-based parsers "
            "(the editor parser and the bot's dynamic-config reader read only the first line "
            f"-> value becomes '{multiline_hits and multiline_hits[0].split('= ')[-1].strip(' .')}'). "
            "Collapse each to a single physical line.",
            " | ".join(multiline_hits[:8]),
        ))
    else:
        findings.append(Finding("OK", "config-parse", "No multi-line list/dict config values detected in config.py"))

    # 2) Duplicate top-level KEY definitions. A re.search-based reader returns the FIRST
    #    match, so a later "readable" redefinition can be silent dead code.
    seen: dict[str, list[int]] = {}
    for idx, line in enumerate(lines, start=1):
        if line[:1].isspace():
            continue  # only column-0 assignments are config settings
        m = _TOP_LEVEL_ASSIGN.match(line)
        if m:
            seen.setdefault(m.group(1), []).append(idx)
    dupes = {key: locs for key, locs in seen.items() if len(locs) > 1}
    if dupes:
        sample = "; ".join(f"{key} @ lines {locs}" for key, locs in list(dupes.items())[:6])
        findings.append(Finding(
            "WARN", "config-parse",
            "Duplicate top-level definitions in config.py; a re.search-based reader returns the "
            "FIRST match, so later redefinitions may be dead code. Keep one definition per key.",
            sample,
        ))
    else:
        findings.append(Finding("OK", "config-parse", "No duplicate top-level config keys detected in config.py"))

    return findings


def diagnose(repo: Path) -> list[Finding]:
    findings: list[Finding] = []
    files = {name: repo / name for name in CORE_FILES}
    texts: dict[str, str] = {}

    for name, path in files.items():
        if path.exists():
            texts[name] = read_text(path)
            findings.append(Finding("OK", "files", f"Found {name}", str(path)))
        else:
            findings.append(Finding("FAIL", "files", f"Missing expected file: {name}", str(path)))

    config = texts.get("config.py", "")
    editor = texts.get("config_editor.py", "")
    bot = texts.get("bot.py", "")
    voice = texts.get("voice_profile.py", "")

    # Config parsing traps (the most common silent bug class in this bot shape).
    findings.extend(check_config_parsing(config))

    if config and "LISTEN_LIST" in config:
        findings.append(Finding("OK", "routing", "config.py defines LISTEN_LIST", grep_context(config, r"LISTEN_LIST\s*=")))
    else:
        findings.append(Finding("FAIL", "routing", "LISTEN_LIST not found in config.py"))

    if bot and "LISTEN_LIST" in bot and "prompt_mapping" in bot:
        findings.append(Finding("OK", "routing", "bot.py appears to route chats from LISTEN_LIST"))
    elif bot:
        findings.append(Finding("WARN", "routing", "bot.py may not be using LISTEN_LIST for chat routing"))

    if config:
        ok, missing = has_all(config, IMAGE_TRIGGERS)
        status = "OK" if ok else "WARN"
        msg = "config.py contains common image trigger words" if ok else f"config.py missing image triggers: {', '.join(missing)}"
        findings.append(Finding(status, "image", msg, grep_context(config, r"IMAGE_GEN_TRIGGER_KEYWORDS\s*=")))

    if editor:
        ok, missing = has_all(editor, IMAGE_TRIGGERS)
        status = "OK" if ok else "WARN"
        msg = "config_editor.py contains common image trigger defaults" if ok else f"config_editor.py missing image trigger defaults: {', '.join(missing)}"
        findings.append(Finding(status, "image", msg, grep_context(editor, r"IMAGE_GEN_TRIGGER_KEYWORDS")))

    if bot:
        placeholder_hits = [marker for marker in IMAGE_PLACEHOLDERS if marker in bot]
        if placeholder_hits and "wx.SendFiles" in bot:
            findings.append(Finding("OK", "image", "bot.py contains image placeholders and wx.SendFiles; inspect that placeholders become file sends", ", ".join(placeholder_hits)))
        elif "wx.SendFiles" in bot:
            findings.append(Finding("WARN", "image", "bot.py sends files but common image placeholders were not found; verify placeholder parsing"))
        else:
            findings.append(Finding("FAIL", "image", "wx.SendFiles not found in bot.py; generated media may not reach WeChat"))

    for name, text in (("config.py", config), ("config_editor.py", editor), ("bot.py", bot)):
        if not text:
            continue
        if VOICE_TOGGLE in text:
            findings.append(Finding("OK", "voice-toggle", f"{name} references {VOICE_TOGGLE}", grep_context(text, VOICE_TOGGLE)))
        else:
            findings.append(Finding("WARN", "voice-toggle", f"{name} does not reference {VOICE_TOGGLE}"))

    if editor and "_build_voice_target_options" in editor and "LISTEN_LIST" in editor:
        findings.append(Finding("OK", "voice-mapping", "config_editor.py appears to build voice targets from LISTEN_LIST"))
    elif editor:
        findings.append(Finding("WARN", "voice-mapping", "Voice target builder from LISTEN_LIST not found in config_editor.py"))

    if voice and "resolve_voice_profile" in voice:
        if "user_key" in voice:
            findings.append(Finding("OK", "voice-mapping", "voice_profile.py supports user_key-aware voice resolution"))
        else:
            findings.append(Finding("WARN", "voice-mapping", "resolve_voice_profile exists but user_key support was not detected"))

    if bot and "resolve_voice_profile" in bot:
        if "user_key" in bot:
            findings.append(Finding("OK", "voice-mapping", "bot.py passes or references user_key for voice resolution"))
        else:
            findings.append(Finding("WARN", "voice-mapping", "bot.py resolves voice profiles but user_key was not detected"))

    return findings


def print_text(findings: list[Finding]) -> None:
    order = {"FAIL": 0, "WARN": 1, "OK": 2}
    for item in sorted(findings, key=lambda finding: (order.get(finding.status, 9), finding.area)):
        print(f"[{item.status}] {item.area}: {item.message}")
        if item.evidence:
            print(f"  evidence: {item.evidence}")


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Static diagnostics for Python chat bot repos.")
    parser.add_argument("--repo", default=".", help="Path to the chat bot repo root")
    parser.add_argument("--json", action="store_true", help="Emit JSON findings")
    args = parser.parse_args(argv)

    repo = Path(args.repo).resolve()
    findings = diagnose(repo)

    if args.json:
        print(json.dumps([finding.as_dict() for finding in findings], ensure_ascii=False, indent=2))
    else:
        print_text(findings)

    return 1 if any(finding.status == "FAIL" for finding in findings) else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
