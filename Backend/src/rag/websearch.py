"""Recherche web de secours (Tavily), sans dépendance LangChain."""

from collections.abc import Awaitable, Callable

from config.settings import get_settings
from src.rag.schemas import SourceDocument

WebSearch = Callable[[str], Awaitable[list[SourceDocument]]]


def tavily_search(max_results: int = 3) -> WebSearch | None:
    """Retourne la fonction de recherche web, ou None si `TAVILY_API_KEY` est absente."""
    api_key = get_settings().TAVILY_API_KEY
    if not api_key:
        return None

    async def search(query: str) -> list[SourceDocument]:
        from tavily import AsyncTavilyClient

        response = await AsyncTavilyClient(api_key=api_key).search(query, max_results=max_results)
        return [
            SourceDocument(number=0, source=r["url"], content=r.get("content", ""), is_web=True)
            for r in response.get("results", [])
        ]

    return search
