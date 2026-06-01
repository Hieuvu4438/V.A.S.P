"""ISSN normalization helper."""

import re


def normalize_issn(issn: str) -> str:
    """Remove separators, capitalize final check character.

    Examples:
        '1234-5678' -> '12345678'
        '1234-567x' -> '1234567X'
    """
    if not issn:
        return ""
    cleaned = re.sub(r"[^0-9a-zA-Z]", "", issn).strip().upper()
    return cleaned
