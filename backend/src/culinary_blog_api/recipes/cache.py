"""Small in-process cache for anonymous recipe-list responses.

FR-RCP-001 requires a 15 minute collection cache keyed by path and query string. The
authenticated collection is intentionally never cached here: its visibility changes by
user and role, so sharing a cache entry could expose a draft or archived recipe.
"""

from __future__ import annotations

import time

from .schemas import PagedRecipeResponse

RECIPE_LIST_CACHE_TTL_SECONDS = 15 * 60


class RecipeListCache:
    def __init__(self) -> None:
        self._entries: dict[str, tuple[float, PagedRecipeResponse]] = {}

    def get(self, key: str) -> PagedRecipeResponse | None:
        entry = self._entries.get(key)
        if entry is None:
            return None
        expires_at, response = entry
        if expires_at <= time.monotonic():
            self._entries.pop(key, None)
            return None
        return response.model_copy(deep=True)

    def set(self, key: str, response: PagedRecipeResponse) -> None:
        self._entries[key] = (
            time.monotonic() + RECIPE_LIST_CACHE_TTL_SECONDS,
            response.model_copy(deep=True),
        )

    def clear(self) -> None:
        self._entries.clear()


recipe_list_cache = RecipeListCache()
