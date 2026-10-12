"""Analyse de la question : filtres métier (société, exercice, type) et question autonome.

Sans historique, aucun appel LLM : les filtres sont déduits des sociétés réellement indexées.
Avec historique, un appel LLM à sortie structurée produit la question autonome."""

import re
from collections.abc import Awaitable, Callable

from langchain_core.language_models import BaseChatModel

from src.rag.schemas import QueryAnalysis
from src.rag.store import Filters

Analyzer = Callable[[str, str], Awaitable[QueryAnalysis]]

_YEAR = re.compile(r"\b((?:19|20)\d{2})\b")
_FY = re.compile(r"\bFY\s?'?(\d{2}|\d{4})\b", re.IGNORECASE)


def _norm(text: str) -> str:
    return re.sub(r"[^a-z0-9]", "", text.lower())


def detect_company(question: str, companies: list[str]) -> str | None:
    """Société connue citée dans la question (comparaison insensible à la casse/ponctuation,
    jusqu'à 4 mots consécutifs : « American Express » -> AMERICANEXPRESS). Plus long d'abord."""
    words = re.findall(r"[A-Za-z0-9&.\-]+", re.sub(r"['’]s\b", "", question))
    grams = {
        _norm(" ".join(words[i : i + n])) for n in range(1, 5) for i in range(len(words) - n + 1)
    }
    known = {_norm(c): c for c in companies if _norm(c)}
    matches = [norm for norm in known if norm in grams]
    return known[max(matches, key=len)] if matches else None


def detect_year(question: str) -> int | None:
    years = {int(y) for y in _YEAR.findall(question)}
    for short in _FY.findall(question):
        years.add(int(short) if len(short) == 4 else 2000 + int(short))
    return years.pop() if len(years) == 1 else None  # ambigu (comparaison) : pas de filtre


def detect_doc_type(question: str) -> str | None:
    lowered = question.lower()
    if re.search(r"10-?q|quarter", lowered):
        return "10-Q"
    if re.search(r"10-?k|annual|fiscal year", lowered):
        return "10-K"
    return None


def heuristic_filters(question: str, companies: list[str]) -> Filters:
    return Filters(
        company=detect_company(question, companies),
        fiscal_year=detect_year(question),
        doc_type=detect_doc_type(question),
    )


ANALYSIS_PROMPT = """Voici l'historique d'une conversation puis la dernière question de l'utilisateur.
Reformule la dernière question pour qu'elle soit compréhensible seule (remplace les pronoms et
sous-entendus par les société, exercice et notion concernés). Ne réponds pas à la question.
Si la société, l'exercice ou le type de document (10-K, 10-Q, 8-K) sont identifiables, renseigne-les.

Historique :
{history}

Dernière question : {question}"""


def llm_analyzer(llm: BaseChatModel) -> Analyzer:
    structured = llm.with_structured_output(QueryAnalysis)

    async def analyze(question: str, history: str) -> QueryAnalysis:
        result = await structured.ainvoke(
            ANALYSIS_PROMPT.format(history=history, question=question)
        )
        assert isinstance(result, QueryAnalysis)
        return result

    return analyze
