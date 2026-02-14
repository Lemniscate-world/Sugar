# Copyright (c) 2026 kuro. All Rights Reserved.
"""Web search connector — search the web via DuckDuckGo (free, no API key)."""

from __future__ import annotations

import logging

from sugar.connectors.base import ActionResult, BaseConnector

logger = logging.getLogger(__name__)


class WebConnector(BaseConnector):
    """Web search connector using DuckDuckGo.

    No API key required. Uses the duckduckgo-search library.
    """

    @property
    def name(self) -> str:
        return "web"

    @property
    def description(self) -> str:
        return "Search the web for information using DuckDuckGo. Free, no API key needed."

    def is_configured(self) -> bool:
        return True  # Always available

    def available_actions(self) -> list[dict[str, str]]:
        return [
            {
                "name": "search",
                "description": "Search the web for information",
                "params": "query (required: search text), max_results (optional, default 5)",
            },
            {
                "name": "news",
                "description": "Search recent news articles",
                "params": "query (required: search text), max_results (optional, default 5)",
            },
        ]

    def execute(self, action: str, params: dict) -> ActionResult:
        handlers = {
            "search": self._search,
            "news": self._news,
        }
        handler = handlers.get(action)
        if not handler:
            return ActionResult(success=False, data=f"Unknown action: {action}")
        try:
            return handler(params)
        except ImportError:
            return ActionResult(
                success=False,
                data="duckduckgo-search not installed. Run: pip install duckduckgo-search",
            )
        except Exception as e:
            logger.error("Web %s failed: %s", action, e)
            return ActionResult(success=False, data=f"Search error: {e}")

    def _search(self, params: dict) -> ActionResult:
        from duckduckgo_search import DDGS

        query = params.get("query", "")
        if not query:
            return ActionResult(success=False, data="Missing 'query' parameter.")

        max_results = params.get("max_results", 5)

        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_results))

        if not results:
            return ActionResult(success=True, data=f"No results for '{query}'.")

        lines = []
        for r in results:
            lines.append(f"- **{r.get('title', 'N/A')}**")
            lines.append(f"  {r.get('body', '')[:150]}")
            lines.append(f"  🔗 {r.get('href', 'N/A')}")

        return ActionResult(
            success=True,
            data=f"Search results for '{query}':\n" + "\n".join(lines),
            raw=results,
        )

    def _news(self, params: dict) -> ActionResult:
        from duckduckgo_search import DDGS

        query = params.get("query", "")
        if not query:
            return ActionResult(success=False, data="Missing 'query' parameter.")

        max_results = params.get("max_results", 5)

        with DDGS() as ddgs:
            results = list(ddgs.news(query, max_results=max_results))

        if not results:
            return ActionResult(success=True, data=f"No news for '{query}'.")

        lines = []
        for r in results:
            lines.append(f"- **{r.get('title', 'N/A')}** ({r.get('date', 'N/A')})")
            lines.append(f"  {r.get('body', '')[:150]}")
            lines.append(f"  🔗 {r.get('url', 'N/A')}")

        return ActionResult(
            success=True,
            data=f"News for '{query}':\n" + "\n".join(lines),
            raw=results,
        )
