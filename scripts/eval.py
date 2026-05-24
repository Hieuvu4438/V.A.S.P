import argparse
import asyncio
import json
from collections import Counter
from typing import Any, cast
from pathlib import Path
from uuid import uuid4

from reviewagent.agents.graph import ReviewPipeline
from reviewagent.schemas.decision import DecisionLabel


DEFAULT_DATASET: list[dict[str, Any]] = [
    {"doi": "10.1109/5.771073", "expected_decision": "APPROVE"},
]


def _load_dataset(path: str | None) -> list[dict[str, Any]]:
    if path is None:
        return DEFAULT_DATASET

    data: Any = json.loads(Path(path).read_text(encoding="utf-8"))
    if isinstance(data, list):
        return cast(list[dict[str, Any]], data)
    if isinstance(data, dict) and isinstance(data.get("items"), list):
        return cast(list[dict[str, Any]], data["items"])
    raise ValueError("Dataset must be a JSON list or an object with an 'items' list")


def _safe_label(value: object) -> DecisionLabel | None:
    if value is None:
        return None
    try:
        return DecisionLabel(str(value).upper())
    except ValueError:
        return None


async def _evaluate(items: list[dict[str, Any]]) -> dict[str, Any]:
    pipeline = ReviewPipeline()
    rows: list[dict[str, Any]] = []

    for item in items:
        doi = str(item["doi"])
        expected = _safe_label(item.get("expected_decision"))
        state = await pipeline.run(submission_id=uuid4(), doi=doi)
        predicted = state.decision.decision if state.decision else None
        rows.append(
            {
                "doi": doi,
                "expected": expected.value if expected else None,
                "predicted": predicted.value if predicted else None,
                "source": state.metadata_source,
                "errors": state.errors,
                "correct": expected is not None and predicted == expected,
            }
        )

    return {"rows": rows, "metrics": _metrics(rows)}


def _metrics(rows: list[dict[str, Any]]) -> dict[str, Any]:
    labeled = [row for row in rows if row["expected"] is not None]
    correct = sum(1 for row in labeled if row["correct"])
    predicted = Counter(row["predicted"] for row in rows if row["predicted"] is not None)
    expected = Counter(row["expected"] for row in labeled)

    per_label: dict[str, dict[str, float]] = {}
    for label in DecisionLabel:
        label_value = label.value
        tp = sum(1 for row in labeled if row["expected"] == label_value and row["predicted"] == label_value)
        fp = sum(1 for row in labeled if row["expected"] != label_value and row["predicted"] == label_value)
        fn = sum(1 for row in labeled if row["expected"] == label_value and row["predicted"] != label_value)
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        per_label[label_value] = {
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1": round(f1, 4),
        }

    return {
        "total": len(rows),
        "labeled": len(labeled),
        "accuracy": round(correct / len(labeled), 4) if labeled else None,
        "expected_counts": dict(expected),
        "predicted_counts": dict(predicted),
        "per_label": per_label,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate the Phase 1 DOI review pipeline.")
    parser.add_argument("--dataset", help="JSON list with doi and optional expected_decision fields.")
    parser.add_argument("--output", help="Optional path to write the JSON evaluation report.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report = asyncio.run(_evaluate(_load_dataset(args.dataset)))
    text = json.dumps(report, indent=2, ensure_ascii=False)
    print(text)
    if args.output:
        Path(args.output).write_text(text + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
