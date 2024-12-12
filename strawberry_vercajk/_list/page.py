import functools
import inspect
import typing

import django.core.paginator
import django.db.models
import django.utils.inspect

__all__ = [
    "Page",
    "Paginator",
]


class Paginator[T](django.core.paginator.Paginator):
    object_list: list[T] | django.db.models.QuerySet[T]

    def get_page(self, number: int) -> "Page[T]":
        return super().get_page(number)

    @typing.override
    def _get_page(self, *args: typing.Any, **kwargs: typing.Any) -> "Page[T]":
        return Page(*args, **kwargs)

    @typing.override
    def validate_number(self, number: int) -> int:
        # the default implementation makes a db query to check for total count - we don't want that
        return number


class Page[T](django.core.paginator.Page):
    number: int
    paginator: Paginator[T]
    object_list: list[T] | django.db.models.QuerySet[T]

    def __repr__(self) -> str:
        return f"<Page {self.number}>"

    @functools.cached_property
    def items_count(self) -> int:
        """Return the number of objects on this page."""
        # Is a close copy of django.core.paginator.Paginator.count
        c = getattr(self.object_list, "count", None)
        if callable(c) and not inspect.isbuiltin(c) and django.utils.inspect.method_has_no_args(c):
            return c()
        return len(self.object_list)
