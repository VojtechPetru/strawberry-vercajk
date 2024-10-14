import typing

import django.db.models
import strawberry
from django.conf import settings

from strawberry_vercajk._app_settings import app_settings
from strawberry_vercajk._list.graphql import ListType, PageInput, SortInput
from strawberry_vercajk._list.page import Page, Paginator
from strawberry_vercajk._validation.validator import ValidatedInput

if typing.TYPE_CHECKING:
    from strawberry_vercajk._list.filter import FilterSet


__all__ = (
    "ListRespHandler",
)


class FilterSetInput[T: "FilterSet"](ValidatedInput[T]):
    """Input for filtering a list of objects."""


class ListRespHandler[T: django.db.models.Model]:
    """
    Response handler for QuerySet/list of items.
    Groups logic for processing a common list request - handles pagination, sorting, filtering.
    """

    def __init__(
        self,
        items: type[T] | django.db.models.QuerySet[T] | list[T],
        info: strawberry.Info,
    ) -> None:
        try:
            if issubclass(items, django.db.models.Model):
                items = items._meta.default_manager.all()  # noqa: SLF001
        except TypeError:
            pass
        self.info = info
        self.items = items

    def process(
        self,
        page: "PageInput|None" = strawberry.UNSET,
        sort: "SortInput|None" = strawberry.UNSET,
        filters: "FilterSetInput|None" = strawberry.UNSET,
    ) -> ListType[T]:
        """
        Processes the given object list request data and returns the response.
        :param page: The pagination to apply.
        :param sort: The sorting to apply.
        :param filters: The filters to apply.
         Unless you have a good reason not to, you should leave this on.
        :raises InputExceptionGroup: When the filter input is invalid.
        """
        items = self.items
        if filters:
            filters.clean()  # TODO handle errors
            items = self.apply_filters(items, filters.clean_data)
        items = self.apply_sorting(items, sort)
        items_page = self.apply_pagination(items, page)
        return ListType[T](
            pagination=items_page,
            items=items_page.object_list,
        )

    def apply_pagination(
        self,
        items: django.db.models.QuerySet[T] | list[T],
        page: PageInput | None = strawberry.UNSET,
    ) -> Page[T]:
        """
        Applies the given pagination to the given queryset.
        :param items: The queryset to paginate.
        :param page: The pagination to apply.
        """
        if not page:
            return Paginator[T](items, per_page=app_settings.LIST.DEFAULT_PAGE_SIZE).get_page(1)
        return Paginator[T](items, per_page=page.page_size).get_page(page.page_number)

    def apply_sorting(
        self,
        items: django.db.models.QuerySet[T] | list[T],
        sort: SortInput | None = strawberry.UNSET,
    ) -> django.db.models.QuerySet[T]:
        if not sort:
            return items
        return sort.sort(items)

    def apply_filters(
        self,
        items: django.db.models.QuerySet[T] | list[T],
        filters: "FilterSet|None" = strawberry.UNSET,
    ) -> django.db.models.QuerySet[T]:
        """
        Applies the given filters to the given queryset.
        :param items: The items to filter.
        :param filters: The filters to apply.
        :raises InputExceptionGroup: When the filter input is invalid.
        """
        return filters.filter(items, self.info)
