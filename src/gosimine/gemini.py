from __future__ import annotations

import os
import re
from dataclasses import asdict, dataclass
from typing import Any, Iterable, Sequence

from gosimine.analysis import AnalysisResult
from gosimine.database import Miner, ParameterSnapshot, ResearchEntry


KEYRING_SERVICE = "gosimine"
KEYRING_USERNAME = "gemini_api_key"
DEFAULT_MODEL = "gemini-3.6-flash"


class GeminiError(RuntimeError):
    pass


@dataclass(frozen=True)
class GeminiCitation:
    title: str
    url: str
    start_index: int
    end_index: int


@dataclass(frozen=True)
class GeminiAnswer:
    text: str
    citations: tuple[GeminiCitation, ...]
    search_queries: tuple[str, ...]
    search_suggestions_html: tuple[str, ...]


@dataclass(frozen=True)
class CredentialStatus:
    key: str | None
    vault_available: bool
    source: str | None


class GeminiCredentials:
    def __init__(self) -> None:
        self._session_key: str | None = None

    def get_key(self) -> CredentialStatus:
        vault_key, vault_available = self._vault_key()
        if vault_key:
            return CredentialStatus(vault_key, True, "credential vault")
        if vault_available:
            return CredentialStatus(self._session_key, True, "session memory" if self._session_key else None)
        environment_key = os.environ.get("GEMINI_API_KEY")
        if environment_key:
            return CredentialStatus(environment_key, False, "GEMINI_API_KEY")
        return CredentialStatus(self._session_key, False, "session memory" if self._session_key else None)

    def set_session_key(self, key: str) -> None:
        self._session_key = key.strip() or None

    def save_to_vault(self, key: str) -> bool:
        try:
            import keyring

            keyring.set_password(KEYRING_SERVICE, KEYRING_USERNAME, key)
        except Exception:
            return False
        self._session_key = None
        return True

    @staticmethod
    def _vault_key() -> tuple[str | None, bool]:
        try:
            import keyring

            backend = keyring.get_keyring()
            if getattr(backend, "priority", 0) <= 0:
                return None, False
            return keyring.get_password(KEYRING_SERVICE, KEYRING_USERNAME), True
        except Exception:
            return None, False


def build_miner_context(
    miner: Miner,
    parameters: Sequence[ParameterSnapshot],
    research_entries: Sequence[ResearchEntry],
    analysis: AnalysisResult | None,
) -> str:
    parameter_lines = [
        f"- {snapshot.parameter}: {snapshot.value} {snapshot.unit}; as of {snapshot.as_of_date}"
        for snapshot in parameters
    ]
    research_lines = [
        f"- {entry.entry_date}: {entry.note}; thesis change: {entry.thesis_change}; catalyst: {entry.catalyst}; open question: {entry.open_question}"
        for entry in research_entries
    ]
    references = _unique_urls(
        [snapshot.source for snapshot in parameters]
        + [entry.source for entry in research_entries]
    )
    reference_lines = [f"- {url}" for url in references] or ["- None recorded."]
    analysis_lines = (
        [f"- {name}: {value}" for name, value in asdict(analysis).items()]
        if analysis is not None
        else ["- Analysis unavailable because required local inputs are missing."]
    )
    return "\n".join(
        [
            "Stored Gosimine dossier:",
            f"- Listing: {miner.name} ({miner.ticker})",
            f"- Primary commodity: {miner.primary_commodity}",
            f"- Listing currency: {miner.trading_currency}",
            "Current sourced parameters:",
            *(parameter_lines or ["- None recorded."]),
            "Personal research entries:",
            *(research_lines or ["- None recorded."]),
            "Derived Gosimine analysis outputs (not company-reported facts):",
            *analysis_lines,
            "Unique source references:",
            *reference_lines,
        ]
    )


def _unique_urls(sources: Iterable[str]) -> tuple[str, ...]:
    urls = []
    seen_urls = set()
    for source in sources:
        for url in re.findall(r"https?://[^\s]+", source):
            url = url.rstrip(".,;:")
            if url in seen_urls:
                continue
            seen_urls.add(url)
            urls.append(url)
    return tuple(urls)


class GeminiResearchClient:
    def __init__(self, credentials: GeminiCredentials, model: str = DEFAULT_MODEL) -> None:
        self.credentials = credentials
        self.model = model

    def ask(self, question: str, context: str) -> GeminiAnswer:
        cleaned_question = question.strip()
        if not cleaned_question:
            raise GeminiError("Enter a research question.")
        return self.ask_prompt(_prompt(cleaned_question, context))

    def ask_prompt(self, prompt: str) -> GeminiAnswer:
        if not prompt.strip():
            raise GeminiError("A Gemini prompt is required.")
        credential = self.credentials.get_key()
        if not credential.key:
            raise GeminiError("A Gemini API key is required.")
        try:
            from google import genai

            client = genai.Client(api_key=credential.key)
            interaction = client.interactions.create(
                model=self.model,
                input=prompt,
                tools=[{"type": "google_search"}],
            )
        except Exception as error:
            raise GeminiError(f"Gemini request failed: {error}") from error
        return _parse_interaction(interaction)


def _prompt(question: str, context: str) -> str:
    return (
        "You are Gosimine's mining-stock research assistant. The local dossier below may contain "
        "sourced company facts, personal opinions, and derived calculation outputs. Do not present "
        "a local fact as independently verified. Use Google Search grounding for current external "
        "claims, cite those claims, prefer issuer filings and technical reports, and clearly identify "
        "uncertainty or conflicts. Do not give investment advice. Return only an HTML fragment using "
        "headings, paragraphs, lists, compact tables, and https links. Do not include Markdown, CSS, "
        "JavaScript, images, forms, iframe elements, or a document wrapper.\n\n"
        f"{context}\n\nResearch question: {question}"
    )


def _parse_interaction(interaction: Any) -> GeminiAnswer:
    citations: list[GeminiCitation] = []
    search_queries: list[str] = []
    search_suggestions_html: list[str] = []
    text_parts: list[str] = []
    for step in getattr(interaction, "steps", ()):
        if getattr(step, "type", None) == "google_search_call":
            search_queries.extend(_strings(getattr(getattr(step, "arguments", None), "queries", ())))
        if getattr(step, "type", None) == "google_search_result":
            for result in getattr(step, "result", ()):
                suggestions = getattr(result, "search_suggestions", None)
                if isinstance(suggestions, str):
                    search_suggestions_html.append(suggestions)
        if getattr(step, "type", None) != "model_output":
            continue
        for block in getattr(step, "content", ()):
            text = getattr(block, "text", None)
            if text:
                text_parts.append(text)
            for annotation in getattr(block, "annotations", ()) or ():
                if getattr(annotation, "type", None) != "url_citation":
                    continue
                url = getattr(annotation, "url", "")
                if url:
                    citations.append(
                        GeminiCitation(
                            title=getattr(annotation, "title", url),
                            url=url,
                            start_index=getattr(annotation, "start_index", 0),
                            end_index=getattr(annotation, "end_index", 0),
                        )
                    )
    text = "\n".join(text_parts) or getattr(interaction, "output_text", "")
    if not text:
        raise GeminiError("Gemini returned no text response.")
    return GeminiAnswer(
        text,
        tuple(citations),
        tuple(dict.fromkeys(search_queries)),
        tuple(dict.fromkeys(search_suggestions_html)),
    )


def _strings(values: Iterable[Any]) -> list[str]:
    return [value for value in values if isinstance(value, str)]