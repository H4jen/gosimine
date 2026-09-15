from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


CONTEXT_PLACEHOLDER = "{{miner_context}}"


class PromptDefinitionError(ValueError):
    pass


@dataclass(frozen=True)
class PromptDefinition:
    key: str
    label: str
    template: str

    def render(self, miner_context: str) -> str:
        return self.template.replace(CONTEXT_PLACEHOLDER, miner_context)


def prompt_directory() -> Path:
    return Path(__file__).resolve().parents[2] / "prompts"


def load_prompt_definitions(directory: Path | None = None) -> dict[str, PromptDefinition]:
    prompt_path = directory or prompt_directory()
    definitions: dict[str, PromptDefinition] = {}
    for file_path in sorted(prompt_path.glob("*.json")):
        definition = _load_prompt_definition(file_path)
        if definition.key in definitions:
            raise PromptDefinitionError(f"Duplicate prompt key: {definition.key}")
        definitions[definition.key] = definition
    return definitions


def _load_prompt_definition(file_path: Path) -> PromptDefinition:
    try:
        raw_definition = json.loads(file_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise PromptDefinitionError(f"Cannot read prompt definition {file_path.name}: {error}") from error
    if not isinstance(raw_definition, dict):
        raise PromptDefinitionError(f"Prompt definition {file_path.name} must be a JSON object")
    key = raw_definition.get("key")
    label = raw_definition.get("label")
    template = raw_definition.get("template")
    if not all(isinstance(value, str) and value.strip() for value in (key, label, template)):
        raise PromptDefinitionError(f"Prompt definition {file_path.name} requires key, label, and template")
    if template.count(CONTEXT_PLACEHOLDER) != 1:
        raise PromptDefinitionError(
            f"Prompt definition {file_path.name} must contain {CONTEXT_PLACEHOLDER} exactly once"
        )
    return PromptDefinition(key.strip(), label.strip(), template)