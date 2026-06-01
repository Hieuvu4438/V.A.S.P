import csv
import tempfile
from pathlib import Path

import pytest

from reviewagent.snapshots.mjl import MJLSnapshot, MJLEntry
from reviewagent.snapshots.scimago import SCImagoSnapshot, SCImagoEntry
from reviewagent.snapshots.beall import BeallSnapshot
from reviewagent.snapshots.issn_utils import normalize_issn


# --- MJL tests ---


def _write_csv(path: Path, rows: list[dict[str, str]], delimiter: str = ",") -> None:
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()), delimiter=delimiter)
        writer.writeheader()
        writer.writerows(rows)


def test_mjl_load_and_lookup(tmp_path: Path) -> None:
    csv_path = tmp_path / "mjl.csv"
    _write_csv(csv_path, [
        {"ISSN-L": "0018-9448", "Title": "IEEE Trans Info Theory", "SCIE": "1", "SSCI": "", "AHCI": "", "ESCI": ""},
        {"ISSN-L": "1234-5678", "Title": "Test Journal", "SCIE": "", "SSCI": "1", "AHCI": "", "ESCI": ""},
    ])

    snap = MJLSnapshot()
    count = snap.load(csv_path)

    assert count == 2
    assert snap.size == 2
    assert snap.loaded is True

    entry = snap.lookup("0018-9448")
    assert entry is not None
    assert entry.title == "IEEE Trans Info Theory"
    assert entry.is_scie is True
    assert entry.is_ssci is False

    entry2 = snap.lookup("1234-5678")
    assert entry2 is not None
    assert entry2.is_ssci is True

    assert snap.lookup("0000-0000") is None


def test_mjl_load_missing_file() -> None:
    snap = MJLSnapshot()
    with pytest.raises(FileNotFoundError):
        snap.load("/nonexistent/mjl.csv")


def test_mjl_truthy_values(tmp_path: Path) -> None:
    csv_path = tmp_path / "mjl.csv"
    _write_csv(csv_path, [
        {"ISSN-L": "0000-0001", "Title": "J1", "SCIE": "true", "SSCI": "yes", "AHCI": "x", "ESCI": "1"},
    ])

    snap = MJLSnapshot()
    snap.load(csv_path)
    entry = snap.lookup("0000-0001")
    assert entry is not None
    assert entry.is_scie is True
    assert entry.is_ssci is True
    assert entry.is_ahci is True
    assert entry.is_esci is True


def test_mjl_skips_empty_issn(tmp_path: Path) -> None:
    csv_path = tmp_path / "mjl.csv"
    _write_csv(csv_path, [
        {"ISSN-L": "", "Title": "No ISSN", "SCIE": "1", "SSCI": "", "AHCI": "", "ESCI": ""},
        {"ISSN-L": "1111-2222", "Title": "Has ISSN", "SCIE": "", "SSCI": "", "AHCI": "", "ESCI": ""},
    ])

    snap = MJLSnapshot()
    assert snap.load(csv_path) == 1
    assert snap.lookup("1111-2222") is not None


# --- SCImago tests ---


def test_scimago_load_and_lookup(tmp_path: Path) -> None:
    csv_path = tmp_path / "scimago.csv"
    _write_csv(csv_path, [
        {"ISSN": "0018-9448", "Title": "IEEE TIT", "SJR": "2.15", "SJR Best Quartile": "Q1", "Year": "2023"},
        {"ISSN": "1234-5678", "Title": "Low Q", "SJR": "0.35", "SJR Best Quartile": "Q4", "Year": "2023"},
        {"ISSN": "0018-9448", "Title": "IEEE TIT", "SJR": "1.90", "SJR Best Quartile": "Q1", "Year": "2022"},
    ], delimiter=";")

    snap = SCImagoSnapshot()
    count = snap.load(csv_path)

    assert count == 3
    assert snap.size == 3

    entry = snap.lookup("0018-9448", 2023)
    assert entry is not None
    assert entry.sjr_value == 2.15
    assert entry.quartile == "Q1"
    assert entry.year == 2023

    assert snap.lookup("0018-9448", 2022) is not None
    assert snap.lookup("0018-9448", 2021) is None
    assert snap.lookup("9999-0000", 2023) is None


def test_scimago_load_with_default_year(tmp_path: Path) -> None:
    csv_path = tmp_path / "scimago.csv"
    _write_csv(csv_path, [
        {"ISSN": "1111-2222", "Title": "No Year", "SJR": "1.0", "SJR Best Quartile": "Q2"},
    ], delimiter=";")

    snap = SCImagoSnapshot()
    snap.load(csv_path, default_year=2023)

    entry = snap.lookup("1111-2222", 2023)
    assert entry is not None
    assert entry.quartile == "Q2"


def test_scimago_requires_year_when_no_default(tmp_path: Path) -> None:
    csv_path = tmp_path / "scimago.csv"
    _write_csv(csv_path, [
        {"ISSN": "1111-2222", "Title": "No Year", "SJR": "1.0", "SJR Best Quartile": "Q2"},
    ], delimiter=";")

    snap = SCImagoSnapshot()
    with pytest.raises(ValueError, match="no default_year"):
        snap.load(csv_path)


def test_scimago_lookup_best(tmp_path: Path) -> None:
    csv_path = tmp_path / "scimago.csv"
    _write_csv(csv_path, [
        {"ISSN": "1111-2222", "Title": "J", "SJR": "1.0", "SJR Best Quartile": "Q2", "Year": "2022"},
        {"ISSN": "1111-2222", "Title": "J", "SJR": "1.5", "SJR Best Quartile": "Q1", "Year": "2023"},
    ], delimiter=";")

    snap = SCImagoSnapshot()
    snap.load(csv_path)

    best = snap.lookup_best("1111-2222")
    assert best is not None
    assert best.year == 2023
    assert best.quartile == "Q1"


# --- Beall tests ---


def test_beall_load_and_check_by_issn(tmp_path: Path) -> None:
    csv_path = tmp_path / "beall.csv"
    _write_csv(csv_path, [
        {"ISSN": "0000-1111", "Title": "Predatory Journal A"},
        {"ISSN": "0000-2222", "Title": "Predatory Journal B"},
    ])

    snap = BeallSnapshot()
    count = snap.load(csv_path)

    assert count == 2
    assert snap.is_predatory("0000-1111", "") is True
    assert snap.is_predatory("0000-2222", "Whatever") is True
    assert snap.is_predatory("9999-0000", "") is False


def test_beall_load_and_check_by_title(tmp_path: Path) -> None:
    csv_path = tmp_path / "beall.csv"
    _write_csv(csv_path, [
        {"ISSN": "", "Title": "Journal of Predatory Research"},
    ])

    snap = BeallSnapshot()
    snap.load(csv_path)

    assert snap.is_predatory("", "Journal of Predatory Research") is True
    assert snap.is_predatory("", "journal of predatory research") is True
    assert snap.is_predatory("", "Legit Journal") is False


def test_beall_case_insensitive_title(tmp_path: Path) -> None:
    csv_path = tmp_path / "beall.csv"
    _write_csv(csv_path, [
        {"ISSN": "", "Title": "INTERNATIONAL JOURNAL OF SCIENCE"},
    ])

    snap = BeallSnapshot()
    snap.load(csv_path)

    assert snap.is_predatory("", "international journal of science") is True
    assert snap.is_predatory("", "International Journal of Science") is True


def test_issn_normalization_logic() -> None:
    assert normalize_issn("1234-5678") == "12345678"
    assert normalize_issn("1234-567x") == "1234567X"
    assert normalize_issn(" 1234-567X ") == "1234567X"
    assert normalize_issn("") == ""
    assert normalize_issn(None) == ""


def test_mjl_issn_normalization(tmp_path: Path) -> None:
    csv_path = tmp_path / "mjl.csv"
    _write_csv(csv_path, [
        {"ISSN-L": "1234-567x", "Title": "J1", "SCIE": "1", "SSCI": "", "AHCI": "", "ESCI": ""},
    ])

    snap = MJLSnapshot()
    snap.load(csv_path)

    # Test lookup using normalized variations
    assert snap.lookup("1234-567X") is not None
    assert snap.lookup("1234567x") is not None
    assert snap.lookup("1234-567x") is not None
    assert snap.lookup("1234-567X ").title == "J1"


def test_scimago_issn_normalization_and_multi_value(tmp_path: Path) -> None:
    csv_path = tmp_path / "scimago.csv"
    _write_csv(csv_path, [
        {"ISSN": "1234-567x, 8765-4321", "Title": "J1", "SJR": "2.5", "SJR Best Quartile": "Q1", "Year": "2023"},
        {"ISSN": "1234-567X", "Title": "J1", "SJR": "2.0", "SJR Best Quartile": "Q2", "Year": "2022"},
    ], delimiter=";")

    snap = SCImagoSnapshot()
    snap.load(csv_path)

    # Test lookup for both ISSNs in the multi-value field
    entry1 = snap.lookup("1234567x", 2023)
    entry2 = snap.lookup("8765-4321", 2023)
    assert entry1 is not None
    assert entry2 is not None
    assert entry1.quartile == "Q1"
    assert entry2.quartile == "Q1"

    # Test lookup best (O(1))
    best = snap.lookup_best("1234-567x")
    assert best is not None
    assert best.year == 2023
    assert best.quartile == "Q1"


def test_beall_multi_value_issn(tmp_path: Path) -> None:
    csv_path = tmp_path / "beall.csv"
    _write_csv(csv_path, [
        {"ISSN": "1234-567X; 8765-4321", "Title": "Predatory J"},
    ])

    snap = BeallSnapshot()
    snap.load(csv_path)

    assert snap.is_predatory("1234-567x", "") is True
    assert snap.is_predatory("87654321", "") is True
    assert snap.is_predatory("0000-0000", "") is False


def test_scimago_auto_detect_delimiter(tmp_path: Path) -> None:
    # Semicolon delimited
    csv_path_semi = tmp_path / "scimago_semi.csv"
    _write_csv(csv_path_semi, [
        {"ISSN": "1234-5678", "Title": "J1", "SJR": "1.0", "SJR Best Quartile": "Q2", "Year": "2023"},
    ], delimiter=";")

    # Comma delimited
    csv_path_comma = tmp_path / "scimago_comma.csv"
    _write_csv(csv_path_comma, [
        {"ISSN": "1234-5678", "Title": "J1", "SJR": "1.0", "SJR Best Quartile": "Q2", "Year": "2023"},
    ], delimiter=",")

    snap1 = SCImagoSnapshot()
    assert snap1.load(csv_path_semi) == 1

    snap2 = SCImagoSnapshot()
    assert snap2.load(csv_path_comma) == 1


def test_atomic_loading_prevents_partial_load_and_data_leak(tmp_path: Path) -> None:
    csv_good = tmp_path / "good.csv"
    _write_csv(csv_good, [
        {"ISSN-L": "1111-1111", "Title": "Good Journal", "SCIE": "1", "SSCI": "", "AHCI": "", "ESCI": ""},
    ])

    snap = MJLSnapshot()
    snap.load(csv_good)
    assert snap.size == 1
    assert snap.lookup("1111-1111") is not None

    # Load bad file (missing columns) -> should raise ValueError and NOT modify existing data
    csv_bad = tmp_path / "bad.csv"
    with csv_bad.open("w", encoding="utf-8") as f:
        f.write("wrong_header1,wrong_header2\nvalue1,value2\n")

    with pytest.raises(ValueError):
        snap.load(csv_bad)

    # Size and lookups should remain unchanged
    assert snap.size == 1
    assert snap.lookup("1111-1111") is not None

    # Reloading a different good file should clear the old entries (no accumulation)
    csv_good2 = tmp_path / "good2.csv"
    _write_csv(csv_good2, [
        {"ISSN-L": "2222-2222", "Title": "Another Good Journal", "SCIE": "1", "SSCI": "", "AHCI": "", "ESCI": ""},
    ])
    snap.load(csv_good2)
    assert snap.size == 1
    assert snap.lookup("1111-1111") is None
    assert snap.lookup("2222-2222") is not None
