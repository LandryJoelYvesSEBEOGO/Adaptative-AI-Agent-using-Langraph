"""Juge LLM : exactitude et fidélité d'une réponse, par sortie structurée."""

from typing import Protocol

from pydantic import BaseModel, Field


class Verdict(BaseModel):
    correct: bool = Field(description="La réponse est équivalente à la réponse de référence.")
    faithful: bool = Field(
        description="Chaque affirmation de la réponse est appuyée par les extraits fournis."
    )
    rationale: str = Field(description="Justification en une ou deux phrases.")


class Judge(Protocol):
    def judge(self, question: str, reference: str, answer: str, contexts: list[str]) -> Verdict: ...


JUDGE_PROMPT = """Tu évalues la réponse d'un assistant d'analyse financière.

Question : {question}

Réponse de référence : {reference}

Réponse de l'assistant : {answer}

Extraits cités par l'assistant :
{contexts}

Critères :
- correct : la réponse donne la même information chiffrée ou factuelle que la référence
  (tolère les arrondis, les unités équivalentes et la reformulation ; une absence de réponse
  ou un refus est incorrect).
- faithful : tout ce qui est affirmé figure dans les extraits. Sans extraits, faithful = false
  sauf si la réponse reconnaît ne pas avoir d'information."""


class GroqJudge:
    """Juge fondé sur un modèle Groq (clé `GROQ_API_KEY`), température nulle."""

    def __init__(self, model: str | None = None):
        from langchain_groq import ChatGroq

        from config.settings import get_settings

        settings = get_settings()
        llm = ChatGroq(
            model=model or settings.GROQ_model,
            temperature=0,
            api_key=settings.GROQ_API_KEYS[0] if settings.GROQ_API_KEYS else None,
        )
        self._llm = llm.with_structured_output(Verdict)

    def judge(self, question: str, reference: str, answer: str, contexts: list[str]) -> Verdict:
        excerpts = "\n---\n".join(contexts) if contexts else "(aucun extrait)"
        prompt = JUDGE_PROMPT.format(
            question=question, reference=reference, answer=answer, contexts=excerpts
        )
        return self._llm.invoke(prompt)  # type: ignore[return-value]
