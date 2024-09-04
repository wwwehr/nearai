import json
from pathlib import Path
from textwrap import fill
from typing import Any, Dict, List, Set

from openapi_client.models.entry_information import EntryInformation
from tabulate import tabulate

from nearai.registry import get_registry_folder, registry
from nearai.solvers import SolverStrategy

EVALUATED_ENTRY_METADATA = "evaluated_entry_metadata"


def record_single_score_evaluation(solver_strategy: SolverStrategy, score: float) -> None:
    """Uploads single score evaluation into registry."""
    evaluation_name = solver_strategy.evaluation_name()
    metrics = {evaluation_name: score}
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
        metrics,
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


def evaluations_table(entries: List[EntryInformation], verbose: bool = False) -> None:
    """Prints table of evaluations."""
    rows: Dict[tuple[tuple[str, Any], ...], Dict[str, str]] = {}
    metric_names: Set[str] = set()
    for entry in entries:
        evaluation_name = f"{entry.namespace}/{entry.name}/{entry.version}"
        evaluation_path = registry.download(evaluation_name)
        metrics_path = evaluation_path / "metrics.json"
        with open(metrics_path, "r") as f:
            metrics = json.load(f)
            key = {
                "model": metrics[EVALUATED_ENTRY_METADATA].get("model", ""),
                "agent": metrics[EVALUATED_ENTRY_METADATA].get("agent", ""),
                "namespace": metrics[EVALUATED_ENTRY_METADATA].get("namespace", ""),
                "version": metrics[EVALUATED_ENTRY_METADATA].get("version", ""),
                "provider": metrics[EVALUATED_ENTRY_METADATA].get("provider", ""),
            }

            # Convert the key dictionary to a tuple to use as a key in rows
            key_tuple = tuple(key.items())

            # Initialize the inner dictionary if this key doesn't exist
            if key_tuple not in rows:
                rows[key_tuple] = {}
            rows[key_tuple] = {}

            # Add all other metrics that are not EVALUATED_ENTRY_METADATA
            for metric_name, metric_value in metrics.items():
                if metric_name != EVALUATED_ENTRY_METADATA:
                    rows[key_tuple][metric_name] = str(metric_value)
                    metric_names.add(metric_name)

    header: List[str] = ["model", "agent"]
    if verbose:
        header = ["model", "agent", "namespace", "version", "provider"]
    for metric_name in metric_names:
        header.append(metric_name)

    table = []
    for row_key_tuple, row_metrics in rows.items():
        row_key = dict(row_key_tuple)
        row: List[str] = [fill(row_key["model"]), fill(row_key["agent"])]
        if verbose:
            row.append(fill(row_key["namespace"]))
            row.append(fill(row_key["version"]))
            row.append(fill(row_key["provider"]))
        for metric_name in metric_names:
            row.append(fill(row_metrics.get(metric_name, "")))
        table.append(row)

    print(tabulate(table, headers=header, tablefmt="simple_grid"))
