"""Phase 2 MVP — Journal Quality Agent (Layer 2).

Validates journal quality using offline snapshots (MJL, SCImago, Beall)
and the DOAJ connector.  Produces a ``JournalCheckResult`` with indexing
flags, quartile, SJR, predatory/hijacked status, and a composite score.
"""

import logging
import time

from reviewagent.agents.state import ReviewState
from reviewagent.connectors.doaj import DOAJConnector
from reviewagent.schemas.cms import CanonicalMetadataSchema
from reviewagent.schemas.journal import JournalCheckResult
from reviewagent.snapshots.beall import BeallSnapshot
from reviewagent.snapshots.mjl import MJLSnapshot
from reviewagent.snapshots.scimago import SCImagoSnapshot

logger = logging.getLogger(__name__)


def _compute_score(
    *,
    is_scie: bool,
    is_ssci: bool,
    is_ahci: bool,
    is_esci: bool,
    is_doaj: bool,
    is_predatory: bool,
    is_hijacked: bool,
    quartile: str | None,
) -> float:
    """Composite journal quality score in [0, 1].

    Rules (from phase2_guide.md):
      - WoS Indexed (SCIE / SSCI / AHCI): +0.5
      - ESCI / DOAJ: +0.3
      - Predatory / Hijacked: score = 0.0 immediately
      - Quartile bonus: Q1 +0.3, Q2 +0.2, Q3 +0.1, Q4 +0.0
      - Capped at 1.0
    """
    if is_predatory or is_hijacked:
        return 0.0

    score = 0.0

    # Core indexing
    if is_scie or is_ssci or is_ahci:
        score += 0.5
    elif is_esci or is_doaj:
        score += 0.3

    # Quartile bonus
    quartile_bonus = {"Q1": 0.3, "Q2": 0.2, "Q3": 0.1, "Q4": 0.0}
    score += quartile_bonus.get(quartile, 0.0)

    return min(score, 1.0)


def _build_flags(
    *,
    is_indexed: bool,
    is_predatory: bool | None,
    is_hijacked: bool | None,
    quartile: str | None,
) -> list[str]:
    flags: list[str] = []
    if not is_indexed:
        flags.append("NOT_INDEXED")
    if is_predatory:
        flags.append("PREDATORY")
    if is_hijacked:
        flags.append("HIJACKED")
    if quartile in ("Q3", "Q4"):
        flags.append("LOW_QUARTILE")
    return flags


async def run(state: ReviewState) -> dict:
    """Execute journal quality checks and return a state update."""
    start = time.monotonic()

    cms: CanonicalMetadataSchema | None = state.get("cms")
    if cms is None:
        return {
            "journal_result": None,
            "timing": _elapsed_timing(state, start),
        }

    issn_l = cms.journal.issn_l
    if not issn_l:
        return {
            "journal_result": None,
            "timing": _elapsed_timing(state, start),
        }

    title = cms.journal.title
    pub_year = cms.pub_year

    # --- Snapshot lookups (synchronous, O(1)) ---
    mjl = _get_mjl_snapshot()
    scimago = _get_scimago_snapshot()
    beall = _get_beall_snapshot()

    mjl_entry = mjl.lookup(issn_l) if mjl.loaded else None
    scimago_entry = scimago.lookup(issn_l, pub_year) if scimago.loaded else None
    # Fallback to best available year if exact year miss
    if scimago_entry is None and scimago.loaded:
        scimago_entry = scimago.lookup_best(issn_l)

    is_scie = mjl_entry.is_scie if mjl_entry else False
    is_ssci = mjl_entry.is_ssci if mjl_entry else False
    is_ahci = mjl_entry.is_ahci if mjl_entry else False
    is_esci = mjl_entry.is_esci if mjl_entry else False

    quartile = scimago_entry.quartile if scimago_entry else None
    sjr_value = scimago_entry.sjr_value if scimago_entry else None

    is_predatory = beall.is_predatory(issn_l, title) if beall.loaded else False

    # --- DOAJ connector (async HTTP) ---
    is_doaj = False
    doaj_evidence: dict = {}
    try:
        doaj = DOAJConnector()
        async with doaj:
            info = await doaj.check_journal(issn_l)
            is_doaj = info.in_doaj
            doaj_evidence = {"in_doaj": info.in_doaj, "apc": info.apc, "seal": info.seal}
    except Exception:
        logger.warning("[journal_agent] DOAJ lookup failed for ISSN %s", issn_l, exc_info=True)

    # Hijacked journal check — placeholder (no public API yet)
    is_hijacked = False

    is_indexed = is_scie or is_ssci or is_ahci or is_esci or is_doaj

    score = _compute_score(
        is_scie=is_scie,
        is_ssci=is_ssci,
        is_ahci=is_ahci,
        is_esci=is_esci,
        is_doaj=is_doaj,
        is_predatory=is_predatory,
        is_hijacked=is_hijacked,
        quartile=quartile,
    )

    flags = _build_flags(
        is_indexed=is_indexed,
        is_predatory=is_predatory,
        is_hijacked=is_hijacked,
        quartile=quartile,
    )

    indexes: list[str] = []
    if is_scie:
        indexes.append("SCIE")
    if is_ssci:
        indexes.append("SSCI")
    if is_ahci:
        indexes.append("AHCI")
    if is_esci:
        indexes.append("ESCI")
    if is_doaj:
        indexes.append("DOAJ")

    evidence = {
        "mjl": {
            "found": mjl_entry is not None,
            "is_scie": is_scie,
            "is_ssci": is_ssci,
            "is_ahci": is_ahci,
            "is_esci": is_esci,
        },
        "scimago": {
            "found": scimago_entry is not None,
            "quartile": quartile,
            "sjr_value": sjr_value,
            "year": scimago_entry.year if scimago_entry else None,
        },
        "doaj": doaj_evidence,
        "beall": {"is_predatory": is_predatory},
        "hijacked": {"is_hijacked": is_hijacked},
    }

    result = JournalCheckResult(
        issn_l=issn_l,
        title=title,
        is_indexed=is_indexed,
        indexes=indexes,
        quartile_best=quartile,
        sjr_value=sjr_value,
        is_predatory=is_predatory,
        is_hijacked=is_hijacked,
        flags=flags,
        score=score,
        evidence=evidence,
    )

    return {
        "journal_result": result,
        "timing": _elapsed_timing(state, start),
    }


# ------------------------------------------------------------------
# Snapshot singletons (loaded once per process)
# ------------------------------------------------------------------

_mjl_snapshot: MJLSnapshot | None = None
_scimago_snapshot: SCImagoSnapshot | None = None
_beall_snapshot: BeallSnapshot | None = None


def _get_mjl_snapshot() -> MJLSnapshot:
    global _mjl_snapshot
    if _mjl_snapshot is None:
        _mjl_snapshot = MJLSnapshot()
    return _mjl_snapshot


def _get_scimago_snapshot() -> SCImagoSnapshot:
    global _scimago_snapshot
    if _scimago_snapshot is None:
        _scimago_snapshot = SCImagoSnapshot()
    return _scimago_snapshot


def _get_beall_snapshot() -> BeallSnapshot:
    global _beall_snapshot
    if _beall_snapshot is None:
        _beall_snapshot = BeallSnapshot()
    return _beall_snapshot


def _elapsed_timing(state: ReviewState, start: float) -> dict[str, float]:
    timing = dict(state.get("timing", {}))
    timing["journal_agent"] = round(time.monotonic() - start, 4)
    return timing
