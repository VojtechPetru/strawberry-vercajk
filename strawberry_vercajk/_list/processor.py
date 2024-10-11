import typing

import django.db.models
import strawberry
from django.conf import settings

from strawberry_vercajk._list.graphql import ListType, PageInput, SortInput
from strawberry_vercajk._list.page import Page, Paginator
from strawberry_vercajk._validation.validator import ValidatedInput

if typing.TYPE_CHECKING:
    from strawberry_vercajk._list.filter import Filterset, ListFilterset


class FilterSetInput[T: "Filterset"](ValidatedInput[T]):
    """Input for filtering a list of objects."""


class QSRespHandler[T: django.db.models.Model]:
    """
    Response handler for QuerySet.
    Groups logic for processing a common list request - handles pagination, sorting, filtering.
    """

    def __init__(
        self,
        qs: type[T] | django.db.models.QuerySet[T],
        info: strawberry.Info,
    ) -> None:
        try:
            if issubclass(qs, django.db.models.Model):
                qs = qs._meta.default_manager.all()  # noqa: SLF001
        except TypeError:
            pass
        self.info = info
        self.qs = qs

    def process(
        self,
        page: PageInput | None = strawberry.UNSET,
        sort: SortInput | None = strawberry.UNSET,
        filters: FilterSetInput | None = strawberry.UNSET,
    ) -> ListType[T]:
        """
        Processes the given object list request data and returns the response.
        :param page: The pagination to apply.
        :param sort: The sorting to apply.
        :param filters: The filters to apply.
         Unless you have a good reason not to, you should leave this on.
        :raises InputExceptionGroup: When the filter input is invalid.
        """
        qs = self.qs
        if filters:
            filters.clean()  # TODO handle errors
            qs = self.apply_filters(self.qs, filters.clean_data)
        qs = self.apply_sorting(qs, sort)
        qs_page = self.apply_pagination(qs, page)
        return ListType[T](
            pagination=qs_page,
            items=qs_page.object_list,
        )

    def apply_pagination(
        self,
        qs: django.db.models.QuerySet[T],
        page: PageInput | None = strawberry.UNSET,
    ) -> Page[T]:
        """
        Applies the given pagination to the given queryset.
        :param qs: The queryset to paginate.
        :param page: The pagination to apply.
        """
        if not page:
            return Paginator[T](qs, per_page=settings.GRAPHQL_DEFAULT_PAGE_SIZE).get_page(1)
        return Paginator[T](qs, per_page=page.page_size).get_page(page.page_number)

    def apply_sorting(
        self,
        qs: django.db.models.QuerySet[T],
        sort: SortInput | None = strawberry.UNSET,
    ) -> django.db.models.QuerySet[T]:
        if not sort:
            return qs
        return qs.order_by(*[f"{'-' if o.direction.is_desc else ''}{o.field.value}" for o in sort.ordering])

    def apply_filters(
        self,
        qs: django.db.models.QuerySet[T],
        filters: "Filterset|None" = strawberry.UNSET,
    ) -> django.db.models.QuerySet[T]:
        """
        Applies the given filters to the given queryset.
        :param qs: The queryset to filter.
        :param filters: The filters to apply.
        :raises InputExceptionGroup: When the filter input is invalid.
        """
        return filters.filter(qs, self.info)


class ListRespHandler[T: typing.Any]:
    """
    Response handler for List.
    Groups logic for processing a common list request - handles pagination, sorting, filtering.
    """

    def __init__(
        self,
        data: list[T],
        info: strawberry.Info,
    ) -> None:
        self.data: list[T] = self.filter_for_user(data, info)
        self.info = info

    def process(
        self,
        page: PageInput | None = strawberry.UNSET,
        sort: SortInput | None = strawberry.UNSET,
        filters: FilterSetInput | None = strawberry.UNSET,
    ) -> ListType[T]:
        """
        Processes the given object list request data and returns the response.
        :param page: The pagination to apply.
        :param sort: The sorting to apply.
        :param filters: The filters to apply.
        """
        data = self.apply_filters(self.data, filters)
        sorted_data = self.apply_sorting(data, sort)
        page = self.apply_pagination(sorted_data, page)
        return ListType[T](pagination=page, items=page)

    def apply_pagination(
        self,
        data: list[T],
        page: PageInput | None = strawberry.UNSET,
    ) -> "Page[T]":
        """
        Applies the given pagination to the given list.
        :param data: The list to paginate.
        :param page: The pagination to apply.
        """
        from strawberry_vercajk._list.page import Paginator

        if not page:
            return Paginator[T](data, per_page=settings.GRAPHQL_DEFAULT_PAGE_SIZE).get_page(1)
        return Paginator[T](data, per_page=page.page_size).get_page(page.page_number)

    def apply_sorting(
        self,
        data: list[T],
        sort: SortInput | None = strawberry.UNSET,
    ) -> list[T]:
        if not sort:
            return data
        return sorted(
            data,
            key=lambda item: tuple(
                _SortReverser(getattr(item, o.field.value))
                if o.direction.is_desc
                else getattr(item, o.field.value)
                for o in sort.ordering
            ),
        )

    def apply_filters(
        self,
        data: list[T],
        filters: "ListFilterset|None" = strawberry.UNSET,
    ) -> list[T]:
        """
        Applies the given filters to the given list.
        :param data: The list to filter.
        :param filters: The filters to apply.
        :raises InputExceptionGroup: When the filter input is invalid.
        """
        if not filters:
            return data
        return filters.filter(data)

    def filter_for_user(
        self,
        data: list[T],
        info: strawberry.Info,  # noqa: ARG002
    ) -> list[T]:
        """Hook to filter the list for the current user - e.g., hide stuff he shouldn't see."""
        return data


class _SortReverser:
    """Reverses the order of the given object."""

    def __init__(
        self,
        obj: typing.Any,  # noqa: ANN401
    ) -> None:
        self.obj = obj

    def __eq__(self, other: "_SortReverser") -> bool:
        return other.obj == self.obj

    def __lt__(
        self,
        other: "_SortReverser",
    ) -> bool:
        return other.obj < self.obj
