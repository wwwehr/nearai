import json
from pathlib import Path
from textwrap import fill
from typing import Any, Dict, List

from tabulate import tabulate

from nearai.registry import get_registry_folder, registry
from nearai.solvers import SolverStrategy

EVALUATED_ENTRY_METADATA = "evaluated_entry_metadata"


def record_single_score_evaluation(solver_strategy: SolverStrategy, score: float) -> None:
    """Uploads single score evaluation into registry."""
    evaluation_name = solver_strategy.evaluation_name()
    record_evaluation_metrics(solver_strategy, {evaluation_name: score}, False)


def _prepend_name_to_metrics(evaluation_name: str, metrics: Dict[str, Any]) -> Dict[str, Any]:
    return {f"{evaluation_name}/{key}": value for key, value in metrics.items()}


def record_evaluation_metrics(
    solver_strategy: SolverStrategy, metrics: Dict[str, Any], prepend_evaluation_name: bool = True
) -> None:
    """Uploads evaluation metrics into registry."""
    evaluation_name = solver_strategy.evaluation_name()
    model = ""
    agent = ""
    version = ""

    if model_metadata := solver_strategy.model_metadata():
        model = model_metadata.get("name", "")
        version = model_metadata.get("version", "")

    if agent_metadata := solver_strategy.agent_metadata():
        agent = agent_metadata.get("name", "")
        version = agent_metadata.get("version", "")

    upload_evaluation(
        evaluation_name,
        metrics if not prepend_evaluation_name else _prepend_name_to_metrics(evaluation_name, metrics),
        model,
        agent,
        solver_strategy.evaluated_entry_namespace(),
        version,
        solver_strategy.model_provider(),
    )


def upload_evaluation(
    evaluation_name: str,
    metrics: Dict[str, Any],
    model: str = "",
    agent: str = "",
    namespace: str = "",
    version: str = "",
    provider: str = "",
) -> None:
    """Uploads evaluation into registry.

    `evaluation_name`: a unique name for (benchmark, solver) tuple, e.g. "mbpp" or "live_bench" or "mmlu-5-shot".
    `metrics`: metrics from evaluation.
    `model`: model that was used.
    `agent`: agent that was evaluated, in any.
    `namespace`: namespace of evaluated agent or evaluated model.
    `version`: version of evaluated agent or evaluated model.
    `provider`: provider of model used; pass `local` if running locally.
    """
    key = f"evaluation_{evaluation_name}"
    metrics[EVALUATED_ENTRY_METADATA] = {}
    if agent != "":
        metrics[EVALUATED_ENTRY_METADATA]["agent"] = agent
        key += f"_agent_{agent}"
    if model != "":
        metrics[EVALUATED_ENTRY_METADATA]["model"] = model
        key += f"_model_{model}"
    if namespace != "":
        metrics[EVALUATED_ENTRY_METADATA]["namespace"] = namespace
        key += f"_namespace_{namespace}"
    if version != "":
        metrics[EVALUATED_ENTRY_METADATA]["version"] = version
        key += f"_version_{version}"
    if provider != "":
        metrics[EVALUATED_ENTRY_METADATA]["provider"] = provider
        key += f"_provider_{provider}"

    entry_path = get_registry_folder() / key
    # Create folder entry_path if not present
    entry_path.mkdir(parents=True, exist_ok=True)
    # Write file metrics.json inside
    metrics_file = entry_path / "metrics.json"
    with metrics_file.open("w") as f:
        json.dump(metrics, f, indent=2)

    metadata_path = entry_path / "metadata.json"
    # TODO(#273): Currently that will not update existing evaluation.
    with open(metadata_path, "w") as f:
        json.dump(
            {
                "name": key,
                "version": "0.0.1",
                "description": "",
                "category": "evaluation",
                "tags": [],
                "details": {},
                "show_entry": True,
            },
            f,
            indent=2,
        )

    registry.upload(Path(entry_path), show_progress=True)


def print_evaluation_table(
    rows: List[Dict[str, str]],
    columns: List[str],
    important_columns: List[str],
    all_key_columns: bool,
    all_metrics: bool,
    num_columns: int,
    metric_name_max_length: int,
) -> None:
    """Prints table of evaluations."""
    metric_names = columns[5:] if all_metrics else important_columns[2:]
    _print_metrics_tables(rows, metric_names, num_columns, all_key_columns, metric_name_max_length)


def _shorten_metric_name(name: str, max_length: int) -> str:
    """Shortens metric name if needed."""
    if len(name) <= max_length:
        return name
    keep = max_length - 2  # 2 dots
    beginning = keep // 3
    ending = keep - beginning
    return name[:beginning] + ".." + name[-ending:]


def _print_metrics_tables(
    rows: List[Dict[str, str]],
    metric_names: List[str],
    num_columns: int,
    all_key_columns: bool,
    metric_name_max_length: int,
):
    """Builds table(s) and prints them."""
    # Shorten metric names
    short_metric_names = [_shorten_metric_name(name, metric_name_max_length) for name in metric_names]

    # Prepare the base header and rows
    base_header = ["model", "agent"]
    if all_key_columns:
        base_header.extend(["namespace", "version", "provider"])

    base_rows = []
    for row in rows:
        base_row = [fill(row.pop("model", "")), fill(row.pop("agent", ""))]
        namespace = row.pop("namespace", "")
        version = row.pop("version", "")
        provider = row.pop("provider", "")
        if all_key_columns:
            base_row.extend([fill(namespace), fill(version), fill(provider)])
        base_rows.append((base_row, row))

    n_metrics_per_table = max(1, num_columns - len(base_header))
    # Split metrics into groups
    metric_groups = list(
        zip(
            [
                short_metric_names[i : i + n_metrics_per_table]
                for i in range(0, len(short_metric_names), n_metrics_per_table)
            ],
            [metric_names[i : i + n_metrics_per_table] for i in range(0, len(metric_names), n_metrics_per_table)],
        )
    )

    # Print tables
    for short_group, full_group in metric_groups:
        header = base_header + short_group
        table = []
        for base_row, row_metrics in base_rows:
            table_row = base_row + [fill(str(row_metrics.get(metric, ""))) for metric in full_group]
            table.append(table_row)
        print(tabulate(table, headers=header, tablefmt="simple_grid"))
