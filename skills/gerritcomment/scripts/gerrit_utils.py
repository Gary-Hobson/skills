#!/usr/bin/env python3
"""Shared utilities for Gerrit scripts."""
from __future__ import annotations

import os
from pathlib import Path
from urllib.parse import urlparse


class GerritError(Exception):
    """Base error for Gerrit operations."""


def parse_change_url(url: str) -> tuple[str, str]:
    """Parse Gerrit change URL, return (base_url, change_ref)."""
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        raise GerritError(f"Invalid Gerrit URL: {url}")

    base_url = f"{parsed.scheme}://{parsed.netloc}"
    parts = [p for p in parsed.path.split("/") if p]

    if "+" in parts:
        idx = parts.index("+")
        if idx + 1 < len(parts):
            return base_url, parts[idx + 1]

    raise GerritError("URL must contain '+/<change_ref>'")


def load_env_file():
    """Load .env file from the skill directory."""
    script_dir = Path(__file__).parent
    skill_dir = script_dir.parent
    env_file = skill_dir / ".env"

    if env_file.exists():
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    os.environ.setdefault(key.strip(), value.strip())


def get_config() -> tuple[str, str, str]:
    """Load config from environment, return (base_url, username, password)."""
    load_env_file()

    base_url = os.environ.get("GERRIT_BASE_URL", "").strip()
    username = os.environ.get("GERRIT_USER", "").strip()
    password = os.environ.get("GERRIT_HTTP_PASSWORD", "").strip()

    missing = []
    if not base_url:
        missing.append("GERRIT_BASE_URL")
    if not username:
        missing.append("GERRIT_USER")
    if not password:
        missing.append("GERRIT_HTTP_PASSWORD")

    if missing:
        missing_str = ", ".join(missing)
        raise GerritError(f"Missing environment variables: {missing_str}")

    return base_url, username, password
