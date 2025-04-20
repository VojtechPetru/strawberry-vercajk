from __future__ import annotations
__all__ = [
    "Page",
    "PageableItems",
]
import functools

import typing

import math


class PageableItems[T](typing.Protocol):
    def count(self) -> int: ...
    def slice(self, start: int = 0, end: int | None = None) -> list[T]: ...
    def __getitem__(self, val: slice) -> list[T]: ...


class Page[T]:
    def __init__(self, all_items: PageableItems[T], /, page: int, size: int) -> None:
        self._all_items = all_items
        self._page_num = page
        self._page_size = size

    @functools.cached_property
    def _items_plus_one(self) -> list[T]:
        """Return the number of items on this page plus one."""
        start = (self._page_num - 1) * self._page_size
        if hasattr(self._all_items, "slice"):
            return self._all_items.slice(start, start + self._page_size + 1)
        return list(self._all_items[start:start + self._page_size + 1])

    @property
    def items(self) -> list[T]:
        """Return the items on this page."""
        items_plus_one = self._items_plus_one
        if len(items_plus_one) == self._page_size + 1:
            return items_plus_one[:-1]
        return items_plus_one

    @property
    def items_count(self) -> int:
        """Return the number of items on this page."""
        return len(self.items)

    @property
    def page_size(self) -> int:
        """Return the number of items per page."""
        return self._page_size

    @property
    def current_page(self) -> int:
        """Return the current page number."""
        return self._page_num

    @property
    def total_pages_count(self) -> int:
        """Return the total number of pages."""
        return math.ceil(self.total_items_count / self.page_size)

    @functools.cached_property
    def total_items_count(self) -> int:
        """Return the total number of items."""
        return self._all_items.count()

    @property
    def has_next_page(self) -> bool:
        """Return True if there is a next page."""
        return self._items_plus_one != self._page_size + 1

    @property
    def has_previous_page(self) -> bool:
        """Return True if there is a previous page."""
        return self._page_num > 1




# class Page[T](django.core.paginator.Page):
#     number: int
#     paginator: Paginator[T]
#     object_list: list[T] | django.db.models.QuerySet[T]
#
#     def __repr__(self) -> str:
#         return f"<Page {self.number}>"
#
#     @functools.cached_property
#     def items_count(self) -> int:
#         """Return the number of objects on this page."""
#         # Is a close copy of django.core.paginator.Paginator.count
#         c = getattr(self.object_list, "count", None)
#         if callable(c) and not inspect.isbuiltin(c) and django.utils.inspect.method_has_no_args(c):
#             return c()
#         return len(self.object_list)
#
#     @property
#     def total_items_count(self) -> int:
#         """Return the total number of items."""
#         return self.paginator.count
#
#     @property
#     def page_size(self) -> int:
#         """Return the number of items per page."""
#         return self.paginator.per_page
#
#     @property
#     def total_pages_count(self) -> int:
#         """Return the total number of pages."""
#         return self.paginator.count
#
#     @property
#     def has_previous_page(self) -> bool:
#         """Return True if there is a previous page."""
#         return self.has_previous()
#
#     @property
#     def has_next_page(self) -> bool:
#         """Return True if there is a next page."""
#         return self.has_next()
