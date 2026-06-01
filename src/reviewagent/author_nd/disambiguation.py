"""Author Name Disambiguation (AND) pipeline.

Provides fuzzy matching between a user-claimed name and a list of
author names from the CMS, using Levenshtein ratio and name permutations.
"""

from reviewagent.author_nd.vietnamese import generate_name_permutations, normalize_vietnamese_name


def _levenshtein_ratio(s1: str, s2: str) -> float:
    """Compute Levenshtein similarity ratio in [0, 1].

    1.0 = identical, 0.0 = completely different.
    """
    if s1 == s2:
        return 1.0
    if not s1 or not s2:
        return 0.0

    len1, len2 = len(s1), len(s2)
    # Use single-row DP for memory efficiency
    prev = list(range(len2 + 1))
    curr = [0] * (len2 + 1)

    for i in range(1, len1 + 1):
        curr[0] = i
        for j in range(1, len2 + 1):
            cost = 0 if s1[i - 1] == s2[j - 1] else 1
            curr[j] = min(
                prev[j] + 1,       # deletion
                curr[j - 1] + 1,   # insertion
                prev[j - 1] + cost, # substitution
            )
        prev, curr = curr, prev

    distance = prev[len2]
    max_len = max(len1, len2)
    return 1.0 - (distance / max_len)


def _match_with_permutations(claimed: str, candidate: str) -> float:
    """Best fuzzy score across all name permutations."""
    claimed_norm = normalize_vietnamese_name(claimed)
    candidate_norm = normalize_vietnamese_name(candidate)

    # Exact match after normalization
    if claimed_norm == candidate_norm:
        return 1.0

    # Direct fuzzy match
    best_score = _levenshtein_ratio(claimed_norm, candidate_norm)

    # Try permutations of the claimed name against the candidate
    for perm in generate_name_permutations(claimed):
        if perm == candidate_norm:
            return 1.0
        score = _levenshtein_ratio(perm, candidate_norm)
        best_score = max(best_score, score)

    # Try permutations of the candidate against the claimed
    for perm in generate_name_permutations(candidate):
        if perm == claimed_norm:
            return 1.0
        score = _levenshtein_ratio(claimed_norm, perm)
        best_score = max(best_score, score)

    return best_score


def match_authors(
    claimed_name: str,
    author_names: list[str],
    threshold_exact: float = 0.95,
    threshold_fuzzy: float = 0.70,
) -> tuple[str | None, float, str]:
    """Find the best matching author for *claimed_name*.

    Returns:
        (matched_name, score, method) where method is
        "and_exact", "and_fuzzy", or "none".
    """
    if not claimed_name or not author_names:
        return None, 0.0, "none"

    best_name: str | None = None
    best_score = 0.0

    for author in author_names:
        score = _match_with_permutations(claimed_name, author)
        if score > best_score:
            best_score = score
            best_name = author

    if best_score >= threshold_exact:
        return best_name, best_score, "and_exact"
    elif best_score >= threshold_fuzzy:
        return best_name, best_score, "and_fuzzy"
    else:
        return best_name, best_score, "none"


def normalize_affiliation(affiliation: str) -> str:
    """Basic affiliation normalization for comparison.

    Lowercases, strips common prefixes, collapses whitespace.
    """
    if not affiliation:
        return ""

    import re
    normalized = affiliation.lower().strip()
    # Remove common prefixes
    normalized = re.sub(r"^(the|university of|institute of|department of)\s+", "", normalized)
    # Collapse whitespace
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized


def affiliation_match(claimed: str, cms_affiliations: list[str]) -> bool:
    """Check if claimed affiliation matches any CMS affiliation."""
    if not claimed or not cms_affiliations:
        return False

    claimed_norm = normalize_affiliation(claimed)
    for aff in cms_affiliations:
        aff_norm = normalize_affiliation(aff)
        if not aff_norm:
            continue
        # Substring match after normalization
        if claimed_norm in aff_norm or aff_norm in claimed_norm:
            return True
        # Fuzzy match for short affiliations
        if _levenshtein_ratio(claimed_norm, aff_norm) >= 0.80:
            return True

    return False
