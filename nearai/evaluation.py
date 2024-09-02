import json
from pathlib import Path
from typing import Any, Dict

from hub.api.v1 import registry
from nearai.registry import get_registry_folder
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

    if agent_metadata := solver_strategy.model_metadata():
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
