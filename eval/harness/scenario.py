"""Scenario definition and YAML loading."""

from __future__ import annotations

from pathlib import Path

import yaml

from eval.models import EvalScenario, ScenarioMessage


def load_scenario(path: str | Path) -> EvalScenario:
    """Load a single scenario from a YAML file."""
    path = Path(path)
    with path.open() as f:
        raw = yaml.safe_load(f)

    messages = [
        ScenarioMessage(
            content=m if isinstance(m, str) else m.get("content", ""),
            delay_seconds=m.get("delay_seconds", 0.0) if isinstance(m, dict) else 0.0,
        )
        for m in raw.get("messages", [])
    ]

    return EvalScenario(
        id=raw["id"],
        name=raw["name"],
        category=raw.get("category", ""),
        timeout_seconds=raw.get("timeout_seconds", 120),
        sandbox=raw.get("sandbox", "local"),
        messages=messages,
        expected_behaviors=raw.get("expected_behaviors", []),
        evaluation_criteria=raw.get("evaluation_criteria", []),
    )


def load_scenarios_from_dir(dir_path: str | Path) -> list[EvalScenario]:
    """Load all *.yaml scenarios from a directory."""
    dir_path = Path(dir_path)
    scenarios = []
    for yaml_file in sorted(dir_path.glob("*.yaml")):
        scenarios.append(load_scenario(yaml_file))
    return scenarios
