from pathlib import Path
from typing import Any

from scripts import eval as eval_script


def test_eval_metrics_computes_basic_scores() -> None:
    rows: list[dict[str, Any]] = [
        {"expected": "APPROVE", "predicted": "APPROVE", "correct": True},
        {"expected": "REVIEW", "predicted": "APPROVE", "correct": False},
        {"expected": None, "predicted": "REVIEW", "correct": False},
    ]

    metrics = eval_script._metrics(rows)

    assert metrics["total"] == 3
    assert metrics["labeled"] == 2
    assert metrics["accuracy"] == 0.5
    assert metrics["per_label"]["APPROVE"]["precision"] == 0.5
    assert metrics["per_label"]["APPROVE"]["recall"] == 1.0


def test_eval_loads_list_dataset(tmp_path: Path) -> None:
    dataset = tmp_path / "dataset.json"
    dataset.write_text('[{"doi": "10.1000/test", "expected_decision": "REVIEW"}]', encoding="utf-8")

    assert eval_script._load_dataset(str(dataset)) == [{"doi": "10.1000/test", "expected_decision": "REVIEW"}]
