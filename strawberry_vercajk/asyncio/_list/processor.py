__all__ = [
    "AsyncBaseListRespHandler",
    "AsyncListType",
    "AsyncPageMetadataType",
]

import abc
import typing

import strawberry

from strawberry_vercajk._app_settings import app_settings
from strawberry_vercajk._list.graphql import PageInput, PageMetadataInterface, SortInput
from strawberry_vercajk.asyncio._list.page import AsyncPage, AsyncPageableItems

if typing.TYPE_CHECKING:
    from strawberry_vercajk._list.filter import FilterSet


@strawberry.type(name="Page", description="Pagination metadata.")
class AsyncPageMetadataType(PageMetadataInterface):
    @strawberry.field(description="Current page number.")
    @staticmethod
    def current_page(root: strawberry.Parent["AsyncPage"]) -> int:
        return root.current_page

    @strawberry.field(description="Number of items on this page.")
    @staticmethod
    async def items_count(root: strawberry.Parent["AsyncPage"]) -> int:
        return await root.items_count

    @strawberry.field(description="Total number of items.")
    @staticmethod
    async def total_items_count(root: strawberry.Parent["AsyncPage"]) -> int:
        return await root.total_items_count

    @strawberry.field(description="Number of items per page.")
    @staticmethod
    def page_size(root: strawberry.Parent["AsyncPage"]) -> int:
        return root.page_size

    @strawberry.field(description="Total number of pages.")
    @staticmethod
    async def total_pages_count(root: strawberry.Parent["AsyncPage"]) -> int:
        return await root.total_pages_count

    @strawberry.field(description="Whether there is a previous page.")
    @staticmethod
    async def has_previous_page(root: strawberry.Parent["AsyncPage"]) -> bool:
        return await root.has_previous_page

    @strawberry.field(description="Whether there is a next page.")
    @staticmethod
    async def has_next_page(root: strawberry.Parent["AsyncPage"]) -> bool:
        return await root.has_next_page


@strawberry.type(name="List", description="List of items.")
class AsyncListType[T]:
    pagination: AsyncPageMetadataType
    items: list[T]


class AsyncBaseListRespHandler[T: AsyncPageableItems](abc.ABC):
    """
    Response handler for a list of items.
    Groups logic for processing a common list request - handles pagination, sorting, filtering.
    """

    def __init__(
        self,
        items: T,
        info: strawberry.Info,
        /,
        page_cls: type[AsyncPage] = AsyncPage,
    ) -> None:
        self._info = info
        self._items = items
        self._page_cls = page_cls

    async def process(
        self,
        page: "PageInput|None" = strawberry.UNSET,
        sort: "SortInput|None" = strawberry.UNSET,
        filters: "ValidatedInput|None" = strawberry.UNSET,  # noqa: F821
    ) -> AsyncListType[T]:
        """
        Processes the given object list request data and returns the response.
        :param page: The pagination to apply.
        :param sort: The sorting to apply.
        :param filters: The filters to apply.
         Unless you have a good reason not to, you should leave this on.
        :raises InputExceptionGroup: When the filter input is invalid.
        """
        items = self._items
        if filters:
            filters.clean()  # TODO handle errors
            items = self.apply_filters(items, filters.clean_data)
        items = self.apply_sorting(items, sort)
        items_page = self.apply_pagination(items, page)
        return AsyncListType[T](
            pagination=items_page,
            items=items_page.items,
        )

    def apply_pagination(
        self,
        items: T,
        page: PageInput | None = strawberry.UNSET,
    ) -> AsyncPage[T]:
        """
        Applies the given pagination to the given queryset.
        :param items: The queryset to paginate.
        :param page: The pagination to apply.
        """
        if not page:
            return self._page_cls[T](items, page=1, size=app_settings.LIST.DEFAULT_PAGE_SIZE)
        return self._page_cls[T](items, page=page.page_number, size=page.page_size)

    @abc.abstractmethod
    def apply_sorting(
        self,
        items: T,
        sort: SortInput | None = strawberry.UNSET,
    ) -> T:
        raise NotImplementedError

    @abc.abstractmethod
    def apply_filters(
        self,
        items: T,
        filters: "FilterSet|None" = strawberry.UNSET,
    ) -> T:
        """
        Applies the given filters to the given queryset.
        :param items: The items to filter.
        :param filters: The filters to apply.
        """
        raise NotImplementedError
