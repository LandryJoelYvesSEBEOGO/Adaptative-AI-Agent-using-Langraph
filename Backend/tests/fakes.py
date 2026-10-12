"""Doubles de test du pipeline RAG : faux LLM en streaming, recherche factice."""

import asyncio
import hashlib
import math
import re
from collections.abc import AsyncIterator

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, AIMessageChunk, BaseMessage
from langchain_core.outputs import ChatGeneration, ChatGenerationChunk, ChatResult

from config.settings import get_settings
from src.rag.pipeline import Dependencies
from src.rag.schemas import QueryAnalysis
from src.rag.search import SearchResult
from src.rag.store import Retrieved


class SlowStreamingLLM(BaseChatModel):
    """Modèle factice : émet la réponse mot par mot avec un délai, et compte ses appels."""

    reply: str = "Capex was 1577 million [1]."
    delay: float = 0.15
    calls: list = []

    @property
    def _llm_type(self) -> str:
        return "slow-fake"

    def _generate(self, messages: list[BaseMessage], stop=None, run_manager=None, **kwargs):
        self.calls.append(messages)
        return ChatResult(generations=[ChatGeneration(message=AIMessage(content=self.reply))])

    async def _astream(
        self, messages: list[BaseMessage], stop=None, run_manager=None, **kwargs
    ) -> AsyncIterator[ChatGenerationChunk]:
        self.calls.append(messages)
        for word in self.reply.split(" "):
            await asyncio.sleep(self.delay)
            yield ChatGenerationChunk(message=AIMessageChunk(content=word + " "))


def retrieved(i: int, company="3M", year=2018, page=60) -> Retrieved:
    return Retrieved(
        chunk_id=i,
        document_id=f"doc{i}",
        filename=f"{company}_{year}_10K.pdf",
        content=f"PP&E purchases were 1,577 million (chunk {i})",
        section="Item 7 > Liquidity",
        kind="text",
        page_start=page,
        page_end=page,
        company=company,
        fiscal_year=year,
        doc_type="10-K",
    )


def make_deps(llm=None, docs=None, confident=True, web=None, analyzer=None, seen=None):
    docs = [retrieved(1), retrieved(2)] if docs is None else docs
    searches = [] if seen is None else seen

    def search(query, filters):
        searches.append((query, filters))
        return SearchResult(docs, 0.9 if confident else 0.01)

    async def default_analyzer(question, history):
        return QueryAnalysis(standalone_question=f"{question} (standalone)")

    return Dependencies(
        llm=llm or SlowStreamingLLM(calls=[]),
        analyze=analyzer or default_analyzer,
        search=search,
        list_companies=lambda: ["3M", "ADOBE", "AMERICANEXPRESS"],
        web_search=web,
    )


class HashEmbedder:
    """Embedding déterministe par sac de mots hachés : similaire si les mots se recoupent."""

    dim = get_settings().EMBEDDING_DIM

    def _vec(self, text: str) -> list[float]:
        vec = [0.0] * self.dim
        for word in re.findall(r"[a-z0-9]+", text.lower()):
            vec[int(hashlib.md5(word.encode()).hexdigest(), 16) % self.dim] += 1.0
        norm = math.sqrt(sum(x * x for x in vec)) or 1.0
        return [x / norm for x in vec]

    def embed_documents(self, texts):
        return [self._vec(t) for t in texts]

    def embed_query(self, text):
        return self._vec(text)
