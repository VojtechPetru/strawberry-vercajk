__all__ = (
    "PageMetadataInterface",
    "PageMetadataType",
    "PageInnerMetadataType",
    "ListType",
    "ListInnerType",
    "PageInput",
    "UnconstrainedPageInput",
    "SortFieldInput",
    "SortInput",
)

import enum
import typing

import strawberry

from strawberry_vercajk._app_settings import app_settings
from strawberry_vercajk._list.sort import OrderingDirection, OrderingNullsPosition

if typing.TYPE_CHECKING:
    from strawberry_vercajk._list.page import Page

_MAX_PAGE_NUMBER: int = 999_999_999
_RETURN_ALL_ITEMS: int = -1  # a flag used to indicate that all items should be returned


@strawberry.type(name="PageInterface", description="List pagination interface.")
class PageMetadataInterface:
    current_page: int
    page_size: int
    items_count: int
    has_next_page: bool
    has_previous_page: bool


@strawberry.type(name="PageInner", description="Pagination metadata.")
class PageInnerMetadataType(PageMetadataInterface):
    pass


@strawberry.type(name="Page", description="Pagination metadata.")
class PageMetadataType(PageMetadataInterface):
    @strawberry.field(description="Current page number.")
    def current_page(self: "Page") -> int:
        return self.number

    @strawberry.field(description="Number of items on this page.")
    def items_count(self: "Page") -> int:
        return self.items_count

    @strawberry.field(description="Total number of items.")
    def total_items_count(self: "Page") -> int:
        return self.paginator.count

    @strawberry.field(description="Number of items per page.")
    def page_size(self: "Page") -> int:
        return self.paginator.per_page

    @strawberry.field(description="Total number of pages.")
    def total_pages_count(self: "Page") -> int:
        return self.paginator.num_pages

    @strawberry.field(description="Whether there is a previous page.")
    def has_previous_page(self: "Page") -> bool:
        return self.has_previous()

    @strawberry.field(description="Whether there is a next page.")
    def has_next_page(self: "Page") -> bool:
        return self.has_next()


@strawberry.type(name="List", description="List of items.")
class ListType[T]:
    pagination: PageMetadataType
    items: list[T]


@strawberry.type(name="ListInner", description="List of items nested in a query.")
class ListInnerType[T]:
    pagination: PageInnerMetadataType
    items: list[T]


@strawberry.input
class PageInput:
    page_number: int = strawberry.field(
        default=1,
        description=f"Page number. Minimum value is 1, maximum is {_MAX_PAGE_NUMBER:,}.",
    )
    page_size: int = strawberry.field(
        default=1,
        description=f"Number of items returned. Minimum value is 1, maximum is {app_settings.LIST.MAX_PAGE_SIZE}.",
    )

    def __setattr__(
        self,
        key: str,
        value: typing.Any,  # noqa: ANN401
    ) -> None:
        if key == "page_number":
            value = min(value, _MAX_PAGE_NUMBER)
            value = max(value, 1)
        elif key == "page_size":
            value = min(value, app_settings.LIST.MAX_PAGE_SIZE)
            value = max(value, 1)
        super().__setattr__(key, value)

    def __hash__(self) -> int:
        return hash((self.page_number, self.page_size))


@strawberry.input
class UnconstrainedPageInput:
    """
    Page input that allows for a page size of -1, which will return all items.
    This is dangerous and should only be used in specific cases where we're sure there won't be "too many" items.
    """

    page_number: int = strawberry.field(
        default=1,
        description=f"Page number. Minimum value is 1, maximum is {_MAX_PAGE_NUMBER:,}.",
    )
    page_size: int = strawberry.field(
        default=1,
        description=f"Number of items returned. Minimum value is 1, there is no maximum. "
        f"A value of {_RETURN_ALL_ITEMS} will return all items.",
    )

    def __setattr__(
        self,
        key: str,
        value: typing.Any,  # noqa: ANN401
    ) -> None:
        if key == "page_number":
            value = min(value, _MAX_PAGE_NUMBER)
            value = max(value, 1)
        elif key == "page_size":
            # Workaround for FE to be able to say that it wants all items, we "hack" it to a very high number
            # -> this logic may need to be updated in the future.
            value = 999_999_999 if value == _RETURN_ALL_ITEMS else max(value, 1)
        super().__setattr__(key, value)


@strawberry.input
class SortFieldInput[T: enum.StrEnum]:
    field: T
    direction: OrderingDirection = OrderingDirection.ASC
    nulls: OrderingNullsPosition = OrderingNullsPosition.LAST

    def __hash__(self) -> int:
        return hash((self.field, self.direction, self.nulls))


@strawberry.input(
    description="Input for ordering a list of objects. "
    "The order ordering is important. "
    "The first ordering is the primary ordering, the second is the secondary ordering, etc.",
)
class SortInput[T: type[enum.StrEnum]]:
    ordering: list[SortFieldInput[T]]

    def __hash__(self) -> int:
        return hash(tuple(self.ordering))


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
