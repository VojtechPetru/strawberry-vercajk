__all__ = [
    "FKListDataLoader",
    "FKListDataLoaderFn",
]

import abc
import functools
import typing

import strawberry

from strawberry_vercajk._app_settings import app_settings
from strawberry_vercajk._dataloaders import core

if typing.TYPE_CHECKING:
    from strawberry_vercajk import FilterQ, ListInnerType, PageInput, SortInput, ValidatedInput


class LoadFn(typing.Protocol):
    def __call__(
        self,
        keys: list[int],
        /,
        *,
        sort: "SortInput",
        filters: "FilterQ",
        start: int = 0,
        size: int = 10,
    ) -> typing.Mapping[typing.Hashable, list]: ...


class FKListDataLoaderFn[K: typing.Hashable, R]:
    @property
    @abc.abstractmethod
    def load_fn(self) -> LoadFn: ...

    def __init__(
        self,
        /,
        page: "PageInput|None" = None,
        sort: "SortInput|None" = None,
        filters: "ValidatedInput|None" = None,
    ) -> None:
        self._page = page
        self._sort = sort
        self._filters = filters

    def __call__(self, keys: list[K]) -> typing.Mapping[K, list[R]]:
        return self.load_fn(
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


class FKListDataLoader[K: typing.Hashable, R](core.BaseDataLoader[K, R]):  # TODO test
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
        load_fn: FKListDataLoaderFn[K, R],
        info: strawberry.Info,
    ) -> None:
        self.load_fn = load_fn
        super().__init__(info=info)

    @property
    def load_fn(self) -> FKListDataLoaderFn[K, R]:
        return self._load_fn

    @load_fn.setter
    def load_fn(self, value: FKListDataLoaderFn[K, R]) -> None:
        self._load_fn = value

    def process_results(self, keys: list[K], results: typing.Mapping[K, list[R]]) -> list["ListInnerType[R]"]:
        import strawberry_vercajk

        page = self.load_fn.page
        key_to_list_type: dict[int, strawberry_vercajk.ListInnerType[R]] = {}
        for id_ in keys:
            items = results.get(id_, [])
            items_count = len(items)
            if items_count > page.page_size:
                items = items[: page.page_size]  # we're getting 1 extra item to check if there's a next page
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


# TODO - re-implement in Django-specific package
# class ReverseFKListDataLoaderFactory(core.BaseDataLoaderFactory[ReverseFKListDataLoader]):
#     """
#     # TODO docstring
#     Base factory for reverse FK relationship dataloaders. For example, get blog posts of a User.
#
#     Example:
#     -------
#         CONSIDER DJANGO MODELS:
#             class User(models.Model):
#                 ...
#
#             class BlogPost(models.Model):
#                 published_by = models.ForeignKey("User", related_name="blog_posts", ...)
#
#         THE FACTORY WOULD BE USED IN THE FOLLOWING MANNER:
#             @strawberry.django.type(models.User)
#             class UserType:
#                 ...
#                 @strawberry.field
#                 async def blog_posts(self: "models.User", info: "Info") -> list["BlogPostType"]:
#                     loader = ReverseFKDataLoaderFactory.make(field_descriptor=User.blog_posts)
#                     return loader(context=info.context).load(self.pk)
#
#     """
#
#     loader_class = ReverseFKListDataLoader
#
#     @classmethod
#     def make(
#         cls,
#         *,
#         _ephemeral: bool = False,
#     ) -> type[ReverseFKListDataLoader]:
#         return super().make(
#             # We can't cache the dataloader class, since its "too specific" (for example, each filter value means
#             # different dataloader) and we could end up with possibly "infinite" number of classes in the memory.
#             _ephemeral=True,
#         )
#
#     @classmethod
#     def generate_loader_name(cls) -> str:
#         field = _get_related_field(config["field_descriptor"])
#         model: type[Model] = field.model
#         meta: Options = model._meta
#         name = (
#             f"{meta.app_label.capitalize()}"
#             f"{meta.object_name}"
#             f"{field.attname.capitalize()}"
#             f"{cls.loader_class.__name__}"
#         )
#         if config.get("page"):
#             name += "Paginated"
#         if config.get("sort"):
#             name += "Sorted"
#         if config.get("filterset"):
#             name += "Filtered"
#         return name
#
#     @classmethod
#     def as_resolver(cls) -> typing.Callable[[typing.Any, strawberry.Info], typing.Any]:
#         # the first arg needs to be called 'root'
#         def resolver(
#             root: "Model",
#             info: "strawberry.Info",
#             page: "PageInput|None" = strawberry.UNSET,
#             sort: "SortInput|None" = strawberry.UNSET,
#             filterset: "FilterSet|None" = strawberry.UNSET,
#         ) -> typing.Any:
#             field_data: StrawberryDjangoField = info._field
#             model: type[Model] = root._meta.model
#             field_descriptor: ReverseManyToOneDescriptor = getattr(model, field_data.django_name)
#             return cls.make(
#                 config={
#                     "field_descriptor": field_descriptor,
#                     "page": page,
#                     "sort": sort,
#                     "filterset": filterset,
#                 },
#             )(info=info).load(root.pk)
#
#         return resolver
