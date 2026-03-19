"""Credential masking utilities for safe display in UI and logs."""
import re


def mask_secret(value: str) -> str:
    if not value or len(value) <= 4:
        return "••••"
    return "••••••••" + value[-4:]


def mask_url(url: str) -> str:
    return re.sub(r'https?://[^@]+@', lambda m: m.group(0).split('//')[0] + '//', url)
