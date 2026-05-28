"""Snapshot updater — Phase 2 MVP.

Downloads fresh CSV files for MJL, SCImago and Beall snapshots,
replaces the on-disk files atomically, and reloads them into memory.

Can be called directly or wrapped by a Celery Beat schedule.

Usage::

    # Direct call (e.g. from a management command or startup hook)
    from reviewagent.snapshots.updater import update_all_snapshots
    await update_all_snapshots()

    # Or individual updates
    await update_mjl_snapshot("snapshots/mjl_current.csv")
"""

import csv
import io
import logging
import shutil
import tempfile
from pathlib import Path

import httpx

from reviewagent.snapshots.beall import BeallSnapshot
from reviewagent.snapshots.mjl import MJLSnapshot
from reviewagent.snapshots.scimago import SCImagoSnapshot

logger = logging.getLogger(__name__)

_DEFAULT_TIMEOUT = httpx.Timeout(connect=15.0, read=60.0, write=10.0, pool=10.0)

# Default source URLs — override via settings or function args
_SCIMAGO_URL = "https://www.scimagojr.com/journalrank.php?out=xls"
_BEALL_URL = "https://raw.githubusercontent.com/stop-hijackers/publishers/main/beall.csv"
# MJL typically requires institutional auth; default is a local file only.
_MJL_URL: str | None = None


# ------------------------------------------------------------------
# Public API
# ------------------------------------------------------------------


async def update_all_snapshots(
    mjl_path: str = "snapshots/mjl_current.csv",
    scimago_path: str = "snapshots/scimago_jcr.csv",
    beall_path: str = "snapshots/beall.csv",
    mjl_url: str | None = _MJL_URL,
    scimago_url: str = _SCIMAGO_URL,
    beall_url: str = _BEALL_URL,
    mjl_snapshot: MJLSnapshot | None = None,
    scimago_snapshot: SCImagoSnapshot | None = None,
    beall_snapshot: BeallSnapshot | None = None,
    default_scimago_year: int | None = None,
) -> dict[str, int]:
    """Download and reload all snapshots. Returns counts per snapshot.

    Pass the live snapshot instances to reload them in-place. When an
    instance is ``None`` the file is still downloaded but not loaded.
    """
    results: dict[str, int] = {}

    results["mjl"] = await update_mjl_snapshot(
        mjl_path, url=mjl_url, snapshot=mjl_snapshot,
    )
    results["scimago"] = await update_scimago_snapshot(
        scimago_path, url=scimago_url, snapshot=scimago_snapshot,
        default_year=default_scimago_year,
    )
    results["beall"] = await update_beall_snapshot(
        beall_path, url=beall_url, snapshot=beall_snapshot,
    )

    logger.info("[updater] All snapshots updated: %s", results)
    return results


async def update_mjl_snapshot(
    path: str,
    *,
    url: str | None = None,
    snapshot: MJLSnapshot | None = None,
) -> int:
    """Download MJL CSV and optionally reload the snapshot.

    If *url* is ``None``, only reloads from the existing file.
    Returns the number of journals loaded (or 0 if no reload).
    """
    if url is not None:
        await _download_and_replace(url, path)
        logger.info("[updater] MJL CSV downloaded to %s", path)

    if snapshot is not None:
        return snapshot.load(path)
    return 0


async def update_scimago_snapshot(
    path: str,
    *,
    url: str = _SCIMAGO_URL,
    snapshot: SCImagoSnapshot | None = None,
    default_year: int | None = None,
) -> int:
    """Download SCImago CSV and optionally reload the snapshot.

    Returns the number of entries loaded (or 0 if no reload).
    """
    await _download_and_replace(url, path)
    logger.info("[updater] SCImago CSV downloaded to %s", path)

    if snapshot is not None:
        return snapshot.load(path, default_year=default_year)
    return 0


async def update_beall_snapshot(
    path: str,
    *,
    url: str = _BEALL_URL,
    snapshot: BeallSnapshot | None = None,
) -> int:
    """Download Beall CSV and optionally reload the snapshot.

    Returns the number of entries loaded (or 0 if no reload).
    """
    await _download_and_replace(url, path)
    logger.info("[updater] Beall CSV downloaded to %s", path)

    if snapshot is not None:
        return snapshot.load(path)
    return 0


# ------------------------------------------------------------------
# Internal helpers
# ------------------------------------------------------------------


async def _download_and_replace(url: str, dest_path: str) -> None:
    """Download *url* to a temp file, then atomically replace *dest_path*.

    Creates parent directories for *dest_path* if they do not exist.
    """
    dest = Path(dest_path)
    dest.parent.mkdir(parents=True, exist_ok=True)

    async with httpx.AsyncClient(timeout=_DEFAULT_TIMEOUT, follow_redirects=True) as client:
        resp = await client.get(url)
        resp.raise_for_status()

    # Write to a temp file in the same directory, then rename
    fd, tmp_name = tempfile.mkstemp(dir=str(dest.parent), suffix=".tmp")
    try:
        with open(fd, "wb") as tmp:
            tmp.write(resp.content)
        shutil.move(tmp_name, str(dest))
    except Exception:
        # Clean up temp file on failure
        Path(tmp_name).unlink(missing_ok=True)
        raise


def _validate_csv(path: str) -> bool:
    """Quick sanity check: file exists and has a header row."""
    p = Path(path)
    if not p.exists():
        return False
    try:
        with p.open(newline="", encoding="utf-8-sig") as fh:
            reader = csv.reader(fh)
            next(reader)
        return True
    except Exception:
        return False
