"""GSTIN (Indian GST Identification Number) format validation.

A GSTIN is 15 chars: 2-digit state code, 10-char PAN, 1 entity digit, a fixed 'Z',
and 1 checksum char. We validate the structural format (docs/FRD); the same regex is
mirrored on the frontend in src/lib/gstin.ts — keep the two in sync.
"""

import re

# ^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[A-Z0-9]{3}$  (state + PAN + entity + Z + checksum)
GSTIN_REGEX = re.compile(r"^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[A-Z0-9]{3}$")


def is_valid_gstin(value: str) -> bool:
    """True if `value` is a structurally valid 15-char GSTIN (case-insensitive)."""
    return bool(GSTIN_REGEX.match(value.strip().upper())) if value else False


def normalize_gstin(value: str) -> str:
    """Canonical GSTIN form: trimmed + uppercased."""
    return value.strip().upper()
