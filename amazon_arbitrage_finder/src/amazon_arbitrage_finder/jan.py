"""JAN/EAN-13 normalisation, checksum validation and extraction from free text.

Rakuten's item search API has no dedicated JAN field, so the code has to be
pulled out of the item name / caption. We only accept checksum-valid codes,
and refuse to guess when a text contains several different codes without a
"JAN" label — a wrong JAN means a wrong ASIN, which is worse than no match.
"""
from __future__ import annotations

import re
import unicodedata

_CODE_RE = re.compile(r"(?<!\d)(\d{13})(?!\d)")
_LABEL_RE = re.compile(r"(JAN|EAN|ＪＡＮ)", re.IGNORECASE)
# How far after a "JAN" label we look for the code, e.g. "JANコード：4901234567894".
_LABEL_WINDOW = 20


def is_valid_ean13(code: str) -> bool:
    if not code or len(code) != 13 or not code.isdigit():
        return False
    digits = [int(c) for c in code]
    total = sum(d * (3 if i % 2 else 1) for i, d in enumerate(digits[:12]))
    return (10 - total % 10) % 10 == digits[12]


def normalize_jan(value) -> str | None:
    """Return a checksum-valid 13-digit JAN from a raw value, or None."""
    if value is None:
        return None
    text = unicodedata.normalize("NFKC", str(value)).strip()
    if text.endswith(".0"):  # numbers read from spreadsheets
        text = text[:-2]
    text = re.sub(r"[\s-]", "", text)
    if len(text) == 12 and text.isdigit():  # UPC-A -> EAN-13
        text = "0" + text
    return text if is_valid_ean13(text) else None


def extract_jan(*texts: str | None) -> str | None:
    """Find the JAN code in free text (item name, caption...).

    Preference order:
    1. a valid code appearing right after a "JAN"/"EAN" label;
    2. the only distinct valid 13-digit code in the text.
    Returns None when nothing valid is found or it is ambiguous.
    """
    joined = "\n".join(unicodedata.normalize("NFKC", t) for t in texts if t)
    if not joined:
        return None

    for label in _LABEL_RE.finditer(joined):
        window = joined[label.end() : label.end() + _LABEL_WINDOW + 13]
        match = _CODE_RE.search(re.sub(r"[\s-]", "", window))
        if match and is_valid_ean13(match.group(1)):
            return match.group(1)

    found = {m.group(1) for m in _CODE_RE.finditer(joined) if is_valid_ean13(m.group(1))}
    if len(found) == 1:
        return found.pop()
    return None
