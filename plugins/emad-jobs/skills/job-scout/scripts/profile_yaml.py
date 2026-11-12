#!/usr/bin/env python3
"""Read profile.yaml with the Python standard library only.

profile.yaml uses a small, strict part of YAML, so the scripts do not need PyYAML:

- mappings: `key: value`, or `key:` followed by an indented block
- lists of plain values: `- value`
- values: quoted or plain strings, whole numbers, decimals, true, false, null, ~, []

Anything else (flow lists such as [a, b], block text with | or >, anchors, tabs) is an
error with a line number. Only `true` and `false` are booleans: `yes`, `no` and `on` stay
strings, so a country code such as NO is never read as false.

Usage (prints the profile as JSON, or the first error):
  python3 profile_yaml.py path/to/profile.yaml
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

KEY_RE = re.compile(r"^([A-Za-z0-9_][A-Za-z0-9_.-]*):(?:\s+(.*))?$")
INT_RE = re.compile(r"^-?\d+$")
FLOAT_RE = re.compile(r"^-?\d+\.\d+$")
UNSUPPORTED_START = ("[", "{", "|", ">", "&", "*", "!", "%", "@", "`")


class ProfileError(ValueError):
    """The profile uses YAML that this reader does not support, or is malformed."""


def _strip_comment(line: str) -> str:
    """Remove a # comment that is outside quotes and starts the line or follows a space."""
    quote = None
    for i, ch in enumerate(line):
        if quote:
            if ch == quote:
                quote = None
        elif ch in ("'", '"'):
            quote = ch
        elif ch == "#" and (i == 0 or line[i - 1] in " \t"):
            return line[:i].rstrip()
    return line.rstrip()


def _scalar(raw: str, lineno: int):
    text = raw.strip()
    if text == "":
        return None
    if text == "[]":
        return []
    if text[0] == '"':
        if len(text) < 2 or not text.endswith('"'):
            raise ProfileError(f"line {lineno}: unclosed double quote")
        return text[1:-1].replace('\\"', '"').replace("\\\\", "\\")
    if text[0] == "'":
        if len(text) < 2 or not text.endswith("'"):
            raise ProfileError(f"line {lineno}: unclosed single quote")
        return text[1:-1].replace("''", "'")
    if text.startswith(UNSUPPORTED_START):
        raise ProfileError(
            f"line {lineno}: {text[:12]!r} is YAML this reader does not support; "
            "use a `- item` list or a quoted string"
        )
    if text in ("true", "false"):
        return text == "true"
    if text in ("null", "~"):
        return None
    if INT_RE.match(text):
        return int(text)
    if FLOAT_RE.match(text):
        return float(text)
    return text


def _tokens(text: str) -> list[tuple[int, int, str]]:
    out = []
    for lineno, line in enumerate(text.splitlines(), start=1):
        body = _strip_comment(line)
        if not body.strip():
            continue
        indent = len(body) - len(body.lstrip(" "))
        if body[indent : indent + 1] == "\t" or "\t" in body[:indent]:
            raise ProfileError(f"line {lineno}: use spaces, not tabs, for indentation")
        out.append((lineno, indent, body[indent:]))
    return out


def _is_item(content: str) -> bool:
    return content == "-" or content.startswith("- ")


def _block(tokens: list, i: int, indent: int):
    """Parse the block that starts at tokens[i] and has this indent. Return (value, next i)."""
    if _is_item(tokens[i][2]):
        items = []
        while i < len(tokens) and tokens[i][1] == indent and _is_item(tokens[i][2]):
            lineno, _, content = tokens[i]
            value = content[1:].strip()
            if value == "":
                raise ProfileError(f"line {lineno}: an empty `-` item is not supported")
            items.append(_scalar(value, lineno))
            i += 1
        if i < len(tokens) and tokens[i][1] > indent:
            raise ProfileError(f"line {tokens[i][0]}: nested lists are not supported")
        return items, i

    mapping: dict = {}
    while i < len(tokens) and tokens[i][1] == indent:
        lineno, _, content = tokens[i]
        if _is_item(content):
            raise ProfileError(f"line {lineno}: a list item where a `key:` was expected")
        match = KEY_RE.match(content)
        if not match:
            raise ProfileError(f"line {lineno}: expected `key: value`, got {content[:40]!r}")
        key, raw = match.group(1), match.group(2)
        if key in mapping:
            raise ProfileError(f"line {lineno}: duplicate key {key!r}")
        i += 1
        if raw is None or raw.strip() == "":
            if i < len(tokens) and tokens[i][1] > indent:
                mapping[key], i = _block(tokens, i, tokens[i][1])
            else:
                mapping[key] = None
        else:
            mapping[key] = _scalar(raw, lineno)
            if i < len(tokens) and tokens[i][1] > indent:
                raise ProfileError(f"line {tokens[i][0]}: unexpected indentation")
    return mapping, i


def loads(text: str) -> dict:
    """Parse profile text into a dict. Raise ProfileError on anything unsupported."""
    tokens = _tokens(text)
    if not tokens:
        return {}
    if tokens[0][1] != 0:
        raise ProfileError(f"line {tokens[0][0]}: the first key must not be indented")
    value, i = _block(tokens, 0, 0)
    if not isinstance(value, dict):
        raise ProfileError(f"line {tokens[0][0]}: the profile must be a mapping, not a list")
    if i < len(tokens):
        raise ProfileError(f"line {tokens[i][0]}: unexpected indentation")
    return value


def load(path: str | Path) -> dict:
    path = Path(path)
    try:
        # utf-8-sig also reads a file that an editor saved with a byte order mark (BOM).
        return loads(path.read_text(encoding="utf-8-sig"))
    except ProfileError as exc:
        raise ProfileError(f"{path}: {exc}") from None


def get(data: dict, dotted: str, default=None):
    """Follow a dotted path such as 'role.target_titles'. Missing or null gives the default."""
    node = data
    for part in dotted.split("."):
        if not isinstance(node, dict) or part not in node:
            return default
        node = node[part]
    return default if node is None else node


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 1 or args[0] in ("-h", "--help"):
        print(__doc__)
        return 0 if args and args[0] in ("-h", "--help") else 2
    try:
        print(json.dumps(load(args[0]), indent=2, ensure_ascii=False))
    except (OSError, ProfileError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
