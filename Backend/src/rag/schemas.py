"""Schémas Pydantic des sorties structurées du pipeline (L3.6)."""

from typing import Literal

from pydantic import BaseModel, Field


class QueryAnalysis(BaseModel):
    """Question autonome et filtres déduits d'une question qui dépend de l'historique."""

    standalone_question: str = Field(
        description="La question reformulée pour être compréhensible sans l'historique."
    )
    company: str | None = Field(
        default=None, description="Société visée, si elle est identifiable."
    )
    fiscal_year: int | None = Field(default=None, description="Exercice visé, si précisé.")
    doc_type: Literal["10-K", "10-Q", "8-K"] | None = Field(
        default=None, description="Type de document visé, si précisé."
    )


class SourceDocument(BaseModel):
    """Passage fourni au modèle de génération (document interne ou résultat web)."""

    number: int
    source: str  # nom de fichier ou URL
    content: str
    is_web: bool = False
    page: int | None = None
    section: str | None = None
    company: str | None = None
    fiscal_year: int | None = None
    doc_type: str | None = None
    document_id: str | None = None
    kind: str = "text"
