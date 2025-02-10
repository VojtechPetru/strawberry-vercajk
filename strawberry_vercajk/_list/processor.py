__all__ = ("BaseListRespHandler",)

import abc
import typing

import strawberry

from strawberry_vercajk._app_settings import app_settings
from strawberry_vercajk._list.graphql import ListType, PageInput, SortInput
from strawberry_vercajk._list.page import Page, Paginator

if typing.TYPE_CHECKING:
    from strawberry_vercajk import ValidatedInput
    from strawberry_vercajk._list.filter import FilterSet


class ItemsType[T](typing.Protocol):
    def __getitem__(self, key: slice) -> typing.Iterable[T]: ...

    def count(self) -> int: ...


class BaseListRespHandler[T](abc.ABC):
    """
    Response handler for QuerySet/list of items.
    Groups logic for processing a common list request - handles pagination, sorting, filtering.
    """

    paginator_cls: type[Paginator[T]] = Paginator

    def __init__(
        self,
        items: ItemsType[T],
        info: strawberry.Info,
    ) -> None:
        self.info = info
        self.items = items

    def process(
        self,
        page: "PageInput|None" = strawberry.UNSET,
        sort: "SortInput|None" = strawberry.UNSET,
        filters: "ValidatedInput|None" = strawberry.UNSET,
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

    @classmethod
    def apply_pagination(
        cls,
        items: ItemsType[T],
        page: PageInput | None = strawberry.UNSET,
    ) -> Page[T]:
        """
        Applies the given pagination to the given queryset.
        :param items: The queryset to paginate.
        :param page: The pagination to apply.
        """
        if not page:
            return cls.paginator_cls[T](items, per_page=app_settings.LIST.DEFAULT_PAGE_SIZE).get_page(1)
        return cls.paginator_cls[T](items, per_page=page.page_size).get_page(page.page_number)

    @abc.abstractmethod
    def apply_sorting(
        self,
        items: ItemsType[T],
        sort: SortInput | None = strawberry.UNSET,
    ) -> ItemsType[T]:
        raise NotImplementedError

    @abc.abstractmethod
    def apply_filters(
        self,
        items: ItemsType[T],
        filters: "FilterSet|None" = strawberry.UNSET,
    ) -> ItemsType[T]:
        """
        Applies the given filters to the given queryset.
        :param items: The items to filter.
        :param filters: The filters to apply.
        """
        raise NotImplementedError
