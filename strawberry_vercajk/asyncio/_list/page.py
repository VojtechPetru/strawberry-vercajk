from __future__ import annotations

__all__ = [
    "AsyncPage",
    "AsyncPageableItems",
]

import math
import typing

import asyncstdlib


class AsyncPageableItems[T](typing.Protocol):
    async def count(self) -> int: ...
    async def slice(self, start: int = 0, end: int | None = None) -> list[T]: ...


class AsyncPage[T]:
    def __init__(self, all_items: AsyncPageableItems[T], /, page: int, size: int) -> None:
        self._all_items = all_items
        self._page_num = max(page, 0)
        self._page_size = max(size, 0)

    @asyncstdlib.cached_property
    async def _items_plus_one(self) -> list[T]:
        """Return the number of items on this page plus one."""
        start = (self._page_num - 1) * self._page_size
        return await self._all_items.slice(start, start + self._page_size + 1)

    @asyncstdlib.cached_property
    async def items(self) -> list[T]:
        """Return the items on this page."""
        items_plus_one = await self._items_plus_one
        if len(items_plus_one) == self._page_size + 1:
            return items_plus_one[:-1]
        return items_plus_one

    @property
    async def items_count(self) -> int:
        """Return the number of items on this page."""
        return len(await self.items)

    @property
    def page_size(self) -> int:
        """Return the number of items per page."""
        return self._page_size

    @property
    def current_page(self) -> int:
        """Return the current page number."""
        return self._page_num

    @asyncstdlib.cached_property
    async def total_pages_count(self) -> int:
        """Return the total number of pages."""
        return math.ceil(await self.total_items_count / self.page_size)

    @asyncstdlib.cached_property
    async def total_items_count(self) -> int:
        """Return the total number of items."""
        return await self._all_items.count()

    @asyncstdlib.cached_property
    async def has_next_page(self) -> bool:
        """Return True if there is a next page."""
        return await self._items_plus_one != self._page_size + 1

    @property
    async def has_previous_page(self) -> bool:
        """Return True if there is a previous page."""
        return self._page_num > 1
