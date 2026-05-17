from dataclasses import dataclass
from typing import Callable

import requests


@dataclass
class ScenarioContext:
    session: requests.Session
    credentials: dict
    auth_state: dict
    credentials_file: object


@dataclass(frozen=True)
class ScenarioDefinition:
    key: str
    label: str
    handler: Callable[[ScenarioContext], None]


_SCENARIO_REGISTRY: dict[str, ScenarioDefinition] = {}


def register_scenario(key: str, label: str):
    def decorator(func: Callable[[ScenarioContext], None]):
        if key in _SCENARIO_REGISTRY:
            raise RuntimeError(f"Scenario key [{key}] is already registered.")

        _SCENARIO_REGISTRY[key] = ScenarioDefinition(
            key=key,
            label=label,
            handler=func,
        )
        return func

    return decorator


def get_registered_scenarios() -> dict[str, ScenarioDefinition]:
    return dict(sorted(_SCENARIO_REGISTRY.items(), key=lambda item: item[0]))