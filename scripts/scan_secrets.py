#!/usr/bin/env python3
"""Scan repository files for likely secrets before publishing a public demo repo."""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

SKIP_DIRS = {
    ".git",
    "venv",
    ".venv",
    "__pycache__",
    "media",
    "staticfiles",
    "seed_assets",
    "node_modules",
}

SKIP_FILES = {
    ".env",
}

SKIP_SCAN_PATHS = {
    "scripts/sanitize_demo_branding.py",
    "scripts/scan_secrets.py",
}

ALLOWED_PLACEHOLDER_PATTERNS = [
    r"replace-with-a-local-development-secret",
    r"change-me-for-local-development",
    r"ChangeMeAdmin123!",
    r"ChangeMeUser123!",
    r"admin@example\.com",
    r"user@example\.com",
    r"noreply@example\.com",
    r"demo-store\.example",
    r"local-development-only",
    r"11111111111",
    r"12345678901",
    r"0000000000",
    r"0000000000000000",
    r"example\.com",
    r"localhost",
    r"demo_admin",
    r"demo_user",
]

PATTERNS = [
    ("ENV_FILE", re.compile(r"^\.env$")),
    ("PRIVATE_KEY", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----")),
    ("AWS_KEY", re.compile(r"AKIA[0-9A-Z]{16}")),
    ("GITHUB_TOKEN", re.compile(r"ghp_[A-Za-z0-9]{20,}")),
    ("SLACK_TOKEN", re.compile(r"xox[baprs]-[A-Za-z0-9-]{10,}")),
    ("JWT", re.compile(r"eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}")),
    ("EMAIL", re.compile(r"[A-Za-z0-9._%+-]+@gmail\.com")),
    ("REAL_PHONE", re.compile(r"\+90\s*554\s*640\s*26\s*14|905546402614")),
    ("DOMAIN", re.compile(r"angelesyasam\.com|www\.angelesyasam\.com", re.I)),
    ("GENERIC_SECRET", re.compile(r"(?i)(api[_-]?key|secret[_-]?key|password)\s*=\s*['\"][^'\"]{8,}['\"]")),
]

TEXT_EXTENSIONS = {
    ".py",
    ".html",
    ".txt",
    ".md",
    ".yml",
    ".yaml",
    ".json",
    ".env",
    ".example",
    ".js",
    ".css",
    ".conf",
}


def is_allowed(match: str) -> bool:
    return any(re.search(pattern, match) for pattern in ALLOWED_PLACEHOLDER_PATTERNS)


def scan_file(path: Path) -> list[tuple[str, int, str]]:
    findings: list[tuple[str, int, str]] = []
    try:
        content = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return findings

    for line_no, line in enumerate(content.splitlines(), start=1):
        for label, pattern in PATTERNS:
            for match in pattern.findall(line):
                value = match if isinstance(match, str) else match[0]
                if is_allowed(value):
                    continue
                findings.append((label, line_no, line.strip()))
    return findings


def main() -> int:
    issues: list[tuple[Path, str, int, str]] = []

    for path in ROOT.rglob("*"):
        if not path.is_file():
            continue
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        if path.name in SKIP_FILES:
            if (ROOT / ".git").exists():
                continue
            issues.append((path, "ENV_FILE", 0, "Local .env file present; ensure it is not committed"))
            continue
        relative = str(path.relative_to(ROOT)).replace("\\", "/")
        if relative in SKIP_SCAN_PATHS:
            continue
        if path.suffix not in TEXT_EXTENSIONS and path.name not in {".env.example"}:
            continue

        for label, line_no, line in scan_file(path):
            issues.append((path, label, line_no, line))

    if not issues:
        print("No likely secrets found.")
        return 0

    print("Potential secrets / sensitive values found:\n")
    for path, label, line_no, line in issues:
        location = f"{path.relative_to(ROOT)}:{line_no}" if line_no else str(path.relative_to(ROOT))
        print(f"[{label}] {location}")
        print(f"  {line}\n")

    return 1


if __name__ == "__main__":
    sys.exit(main())
