__all__ = [
    "AsyncFKListDataLoader",
    "AsyncFKListDataLoaderFn",
]

import functools
import typing

import strawberry

from strawberry_vercajk._app_settings import app_settings
from strawberry_vercajk.asyncio._dataloaders import core

if typing.TYPE_CHECKING:
    from strawberry_vercajk import FilterQ, PageInput, SortInput, ValidatedInput


class LoadFn[K: typing.Hashable](typing.Protocol):
    async def __call__(
        self,
        keys: typing.Sequence[K],
        /,
        *,
        sort: "SortInput",
        filters: "FilterQ",
        start: int = 0,
        size: int = 10,
    ) -> typing.Mapping[K, list]: ...


class AsyncFKListDataLoaderFn[K: typing.Hashable, R]:
    def __init__(
        self,
        load_fn: LoadFn,
        /,
        *,
        page: "PageInput|None" = None,
        sort: "SortInput|None" = None,
        filters: "ValidatedInput|None" = None,
    ) -> None:
        self.load_fn = load_fn
        self._page = page
        self._sort = sort
        self._filters = filters

    async def __call__(self, keys: typing.Sequence[K]) -> typing.Mapping[K, list[R]]:
        return await self.load_fn(
            keys,
            sort=self.sort,
            filters=self.filter_q,
            start=self.page.page_size * (self.page.page_number - 1),
            size=self.page.page_size + 1,  # + 1 check if there is next page
        )

    @property
    def sort(self) -> "SortInput":
        from strawberry_vercajk import SortInput

        return self._sort or SortInput(ordering=[])

    @functools.cached_property
    def filter_q(self) -> "FilterQ":
        from strawberry_vercajk import FilterQ

        if self._filters:
            self._filters.clean()
            return self._filters.clean_data.get_filter_q()
        return FilterQ()

    @property
    def page(self) -> "PageInput":
        from strawberry_vercajk import PageInput

        return self._page or PageInput(page_number=1, page_size=app_settings.LIST.DEFAULT_PAGE_SIZE)


class AsyncFKListDataLoader[K: typing.Hashable, R](core.AsyncDataLoader[K, R]):  # TODO test
    """
    Base loader for reversed FK relationship (e.g., BlogPosts of a User).
    Addi

    EXAMPLE - load blog posts of an account:
        FOR THE FOLLOWING DJANGO MODEL:
            class User(models.Model):
                ...

            class BlogPost(models.Model):
                published_by = models.ForeignKey("User", related_name="blog_posts", ...)

        1. DATALOADER DEFINITION
        class UserBlogPostsFKListDataLoader(ReverseFKDataLoader):
            pass

        2. USAGE
        @strawberry.type(models.User)
        class UserType:
            ...

            @strawberry.field
            def blog_posts(
                self: "models.User",
                filters: <strawberry_vercajk.ValidatedInput instance> | None = strawberry.UNSET,
                sort: strawberry_vercajk.SortInput[BlogPostSortChoices] | None = strawberry.UNSET,
                page: strawberry_vercajk.PageInput | None = strawberry.UNSET,
                info: "Info",
            ) -> list["BlogPostType"]:
                class _LoaderFn(FKListDataLoaderFn):
                    load_fn = get_window_for_service_orders

                return dataloaders.ServiceOrderDeviceListDataLoader(
                    info=info,
                    load_fn=_LoaderFn(page, sort, filters),
                ).load(
                    self.id,
                )
    """

    def __init__(
        self,
        info: strawberry.Info,
        /,
        data_load_fn: AsyncFKListDataLoaderFn[K, R],
    ) -> None:
        self._data_load_fn = data_load_fn
        super().__init__(info=info)

    @typing.final
    @typing.override
    async def _load_fn(
        self,
        keys: typing.Sequence[K],
        /,
    ) -> typing.Sequence[R | BaseException]:
        """
        Function to load the raw results.
        Results can then be further processed by overriding `process_results`.
        """
        import strawberry_vercajk

        data = await self._data_load_fn(keys)

        page = self._data_load_fn.page
        key_to_list_type: dict[K, strawberry_vercajk.ListInnerType[R]] = {}
        for id_ in keys:
            items = data.get(id_, [])
            items_count = len(items)
            if items_count > page.page_size:
                # We're getting 1 extra item to check if there's a next page in AsyncFKListDataLoaderFn.
                items = items[: page.page_size]
            key_to_list_type[id_] = strawberry_vercajk.ListInnerType(
                items=items,
                pagination=strawberry_vercajk.PageInnerMetadataType(
                    current_page=page.page_number,
                    page_size=page.page_size,
                    items_count=items_count - 1 if items_count > page.page_size else items_count,
                    has_next_page=items_count > page.page_size,
                    has_previous_page=page.page_number > 1,
                ),
            )

        return [key_to_list_type.get(id_, []) for id_ in keys]
