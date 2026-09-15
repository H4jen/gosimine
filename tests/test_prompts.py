from pathlib import Path

import pytest

from gosimine.prompts import PromptDefinitionError, load_prompt_definitions


def test_complete_analysis_prompt_loads_and_renders_miner_context() -> None:
    definitions = load_prompt_definitions()

    rendered = definitions["complete_analysis"].render("Stored Gosimine dossier")

    assert definitions["complete_analysis"].label == "Complete analysis"
    assert "{{miner_context}}" not in rendered
    assert "Stored Gosimine dossier" in rendered


def test_prompt_template_requires_exactly_one_context_placeholder(tmp_path: Path) -> None:
    (tmp_path / "invalid.json").write_text(
        '{"key": "invalid", "label": "Invalid", "template": "No context"}',
        encoding="utf-8",
    )

    with pytest.raises(PromptDefinitionError, match="exactly once"):
        load_prompt_definitions(tmp_path)