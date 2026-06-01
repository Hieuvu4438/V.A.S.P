"""Vietnamese name normalization utilities for Author Disambiguation.

Handles Unicode NFC normalization, academic title stripping, and
basic name formatting for fuzzy matching.
"""

import re
import unicodedata

# Academic titles (Vietnamese + international) to strip from names
_TITLE_PATTERNS = [
    r"\bGS\.?\s*",       # Giáo sư
    r"\bPGS\.?\s*",      # Phó Giáo sư
    r"\bTS\.?\s*",       # Tiến sĩ
    r"\bThS\.?\s*",      # Thạc sĩ
    r"\bCN\.?\s*",       # Cử nhân
    r"\bDr\.?\s*",
    r"\bProf\.?\s*",
    r"\bAssoc\.?\s*Prof\.?\s*",
    r"\bMr\.?\s*",
    r"\bMrs\.?\s*",
    r"\bMs\.?\s*",
]
_TITLE_RE = re.compile("|".join(_TITLE_PATTERNS), re.IGNORECASE)

# Suffixes like ", PhD", ", D.Sc."
_SUFFIX_RE = re.compile(r",\s*(PhD|D\.Sc|M\.Sc|MA|MBA)\.?$", re.IGNORECASE)

# Multiple whitespace
_MULTI_SPACE_RE = re.compile(r"\s+")


def normalize_vietnamese_name(name: str) -> str:
    """Normalize a Vietnamese name for matching.

    Steps:
      1. Unicode NFC normalization
      2. Strip academic titles (TS., PGS., GS., Dr., etc.)
      3. Strip degree suffixes (, PhD)
      4. Lowercase
      5. Collapse whitespace and strip
    """
    if not name:
        return ""

    # 1. Unicode NFC
    normalized = unicodedata.normalize("NFC", name)

    # 2. Strip titles
    normalized = _TITLE_RE.sub(" ", normalized)

    # 3. Strip suffixes
    normalized = _SUFFIX_RE.sub("", normalized)

    # 4. Lowercase
    normalized = normalized.lower()

    # 5. Collapse whitespace
    normalized = _MULTI_SPACE_RE.sub(" ", normalized).strip()

    return normalized


def generate_name_permutations(name: str) -> list[str]:
    """Generate common name permutations for matching.

    Example: "Nguyen Van A" -> ["nguyen van a", "a van nguyen",
                                  "a. v. nguyen", "nguyen v. a."]
    """
    normalized = normalize_vietnamese_name(name)
    parts = normalized.split()
    if not parts:
        return [normalized]

    permutations: list[str] = []
    permutations.append(normalized)

    if len(parts) >= 2:
        # Last name first: "a nguyen van"
        last_first = parts[-1:] + parts[:-1]
        permutations.append(" ".join(last_first))

        # Initials format: "n. v. a."
        initials = ". ".join(p[0] for p in parts) + "."
        permutations.append(initials)

        # Last + initials: "a. n. v."
        if len(parts) >= 3:
            last_initials = parts[-1] + ". " + ". ".join(p[0] for p in parts[:-1]) + "."
            permutations.append(last_initials)

        # First name initial + last name: "nguyen v. a."
        if len(parts) >= 3:
            first_last = parts[0] + " " + ". ".join(p[0] for p in parts[1:]) + "."
            permutations.append(first_last)

    return permutations
