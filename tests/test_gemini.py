from types import SimpleNamespace

from gosimine.database import Miner, ParameterSnapshot
from gosimine.gemini import GeminiCredentials, _parse_interaction, build_miner_context


def test_environment_key_is_used_only_when_vault_is_unavailable(monkeypatch) -> None:
    credentials = GeminiCredentials()
    monkeypatch.setenv("GEMINI_API_KEY", "environment-key")
    monkeypatch.setattr(credentials, "_vault_key", lambda: (None, False))

    assert credentials.get_key().source == "GEMINI_API_KEY"
    assert credentials.get_key().key == "environment-key"

    monkeypatch.setattr(credentials, "_vault_key", lambda: (None, True))

    assert credentials.get_key().key is None


def test_miner_context_moves_unique_source_urls_to_the_end() -> None:
    miner = Miner(1, "Example Silver", "EX", "Silver", "Developer", "CAD")
    parameter = ParameterSnapshot(
        1,
        1,
        "aisc_per_ounce",
        19.98,
        "USD/AgEq oz",
        "2026-06-22",
        "Issuer presentation https://example.com/presentation.pdf",
    )

    context = build_miner_context(miner, (parameter,), (), None)

    assert "aisc_per_ounce: 19.98 USD/AgEq oz; as of 2026-06-22" in context
    assert "Issuer presentation" not in context
    assert context.endswith(
        "Unique source references:\n- https://example.com/presentation.pdf"
    )


def test_parse_interaction_preserves_grounded_citations_and_queries() -> None:
    interaction = SimpleNamespace(
        output_text="Fallback",
        steps=[
            SimpleNamespace(
                type="google_search_call",
                arguments=SimpleNamespace(queries=["VZLA feasibility study"]),
            ),
            SimpleNamespace(
                type="google_search_result",
                result=[SimpleNamespace(search_suggestions="<div>Google suggestions</div>")],
            ),
            SimpleNamespace(
                type="model_output",
                content=[
                    SimpleNamespace(
                        text="The company published a feasibility study.",
                        annotations=[
                            SimpleNamespace(
                                type="url_citation",
                                title="Issuer release",
                                url="https://example.com/release",
                                start_index=0,
                                end_index=40,
                            )
                        ],
                    )
                ],
            ),
        ],
    )

    answer = _parse_interaction(interaction)

    assert answer.text == "The company published a feasibility study."
    assert answer.search_queries == ("VZLA feasibility study",)
    assert answer.citations[0].url == "https://example.com/release"
    assert answer.search_suggestions_html == ("<div>Google suggestions</div>",)