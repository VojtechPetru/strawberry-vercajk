import typing
from collections import defaultdict

import strawberry
from django.db.models import F, ForeignKey, Model, Window
from django.db.models.functions import DenseRank

from strawberry_vercajk._app_settings import app_settings
from strawberry_vercajk._dataloaders import core

if typing.TYPE_CHECKING:
    from django.db.models.fields.related_descriptors import ReverseManyToOneDescriptor, ReverseOneToOneDescriptor
    from django.db.models.options import Options
    from strawberry_django.fields.field import StrawberryDjangoField

    from strawberry_vercajk import FilterSet, ListInnerType, PageInput, SortInput


def _get_related_field(field_descriptor: "ReverseManyToOneDescriptor") -> "ForeignKey":
    """
    Get the related field of the reverse FK relationship, i.e., the ForeignKey/OneToOneField field where
    the relationship is defined.
    """
    return field_descriptor.field


__all__ = (
    "ReverseFKListDataLoader",
    "ReverseFKListDataLoaderFactory",
)


class ReverseFKListDataLoaderClassKwargs(typing.TypedDict):
    field_descriptor: "ReverseManyToOneDescriptor|ReverseOneToOneDescriptor"
    page: typing.NotRequired["PageInput|None"]
    sort: typing.NotRequired["SortInput|None"]
    filterset: typing.NotRequired["FilterSet|None"]


class ReverseFKListDataLoader(core.BaseDataLoader):
    # TODO - update docstring
    """
    Base loader for reversed FK relationship (e.g., BlogPosts of a User).

    EXAMPLE - load blog posts of an account:
        FOR THE FOLLOWING DJANGO MODEL:
            class User(models.Model):
                ...

            class BlogPost(models.Model):
                published_by = models.ForeignKey("User", related_name="blog_posts", ...)

        1. DATALOADER DEFINITION
        class UserBlogPostsReverseFKDataLoader(ReverseFKDataLoader):
            field_descriptor = User.blog_posts

        2. USAGE
        @strawberry.django.type(models.User)
        class UserType:
            ...

            @strawberry.field
            def blog_posts(self: "models.User", info: "Info") -> list["BlogPostType"]:
                return UserBlogPostsReverseFKDataLoader(context=info.context).load(self.pk)
    """

    Config: typing.ClassVar[ReverseFKListDataLoaderClassKwargs]

    def load_fn(self, keys: list[int]) -> list["ListInnerType[Model]"]:
        import strawberry_vercajk
        from strawberry_vercajk._list.graphql import PageInnerMetadataType

        field = _get_related_field(self.Config["field_descriptor"])
        model: type[Model] = field.model
        reverse_path: str = field.attname

        filterset = self.Config.get("filterset")
        page = self.Config.get("page")
        sort = self.Config.get("sort")
        if not page:
            page = strawberry_vercajk.PageInput(page_number=1, page_size=app_settings.LIST.DEFAULT_PAGE_SIZE)

        qs = model.objects.filter(**{f"{reverse_path}__in": keys})
        if filterset:
            qs = filterset.filter(qs, info=self.info)
        if sort:
            qs = sort.sort(qs)
        if page:
            qs = qs.annotate(
                rank=Window(
                    expression=DenseRank(),
                    partition_by=[F(reverse_path)],
                    order_by=sort.get_sort_q() if sort else ["pk"],  # needs to be here, otherwise doesn't work
                ),
            ).filter(
                rank__in=range(
                    page.page_number,
                    # + 2 because we need to add 1 to the page size to check if there's a next page
                    page.page_size + 2,
                ),
            )

        # ensure that instances are ordered the same way as input 'ids'
        key_to_instances: dict[int, list[Model]] = defaultdict(list)
        for instance in qs:
            key_to_instances[getattr(instance, reverse_path)].append(instance)

        key_to_list_type: dict[int, strawberry_vercajk.ListInnerType[Model]] = {}
        for id_ in keys:
            items = key_to_instances.get(id_, [])
            items_count = len(items)
            if items_count > page.page_size:
                items = items[: page.page_size]  # we're getting 1 extra item to check if there's a next page
            key_to_list_type[id_] = strawberry_vercajk.ListInnerType(
                items=items,
                pagination=PageInnerMetadataType(
                    current_page=page.page_number,
                    page_size=page.page_size,
                    items_count=items_count - 1 if items_count > page.page_size else items_count,
                    has_next_page=items_count > page.page_size,
                    has_previous_page=page.page_number > 1,
                ),
            )

        return [key_to_list_type.get(id_, []) for id_ in keys]


class ReverseFKListDataLoaderFactory(core.BaseDataLoaderFactory[ReverseFKListDataLoader]):
    """
    # TODO docstring
    Base factory for reverse FK relationship dataloaders. For example, get blog posts of a User.

    Example:
    -------
        CONSIDER DJANGO MODELS:
            class User(models.Model):
                ...

            class BlogPost(models.Model):
                published_by = models.ForeignKey("User", related_name="blog_posts", ...)

        THE FACTORY WOULD BE USED IN THE FOLLOWING MANNER:
            @strawberry.django.type(models.User)
            class UserType:
                ...
                @strawberry.field
                async def blog_posts(self: "models.User", info: "Info") -> list["BlogPostType"]:
                    loader = ReverseFKDataLoaderFactory.make(field_descriptor=User.blog_posts)
                    return loader(context=info.context).load(self.pk)

    """

    loader_class = ReverseFKListDataLoader

    @classmethod
    def make(
        cls,
        *,
        config: ReverseFKListDataLoaderClassKwargs,
        _ephemeral: bool = False,
    ) -> type[ReverseFKListDataLoader]:
        return super().make(
            config=config,
            # We can't cache the dataloader class, since its "too specific" (for example, each filter value means
            # different dataloader) and we could end up with possibly "infinite" number of classes in the memory.
            _ephemeral=True,
        )

    @classmethod
    def generate_loader_name(cls, config: ReverseFKListDataLoaderClassKwargs) -> str:
        field = _get_related_field(config["field_descriptor"])
        model: type[Model] = field.model
        meta: Options = model._meta  # noqa: SLF001
        name = (
            f"{meta.app_label.capitalize()}"
            f"{meta.object_name}"
            f"{field.attname.capitalize()}"
            f"{cls.loader_class.__name__}"
        )
        if config.get("page"):
            name += "Paginated"
        if config.get("sort"):
            name += "Sorted"
        if config.get("filterset"):
            name += "Filtered"
        return name

    @classmethod
    def as_resolver(cls) -> typing.Callable[[typing.Any, strawberry.Info], typing.Any]:
        # the first arg needs to be called 'root'
        def resolver(
            root: "Model",
            info: "strawberry.Info",
            page: "PageInput|None" = strawberry.UNSET,
            sort: "SortInput|None" = strawberry.UNSET,
            filterset: "FilterSet|None" = strawberry.UNSET,
        ) -> typing.Any:  # noqa: ANN401
            field_data: StrawberryDjangoField = info._field  # noqa: SLF001
            model: type[Model] = root._meta.model  # noqa: SLF001
            field_descriptor: ReverseManyToOneDescriptor = getattr(model, field_data.django_name)
            return cls.make(
                config={
                    "field_descriptor": field_descriptor,
                    "page": page,
                    "sort": sort,
                    "filterset": filterset,
                },
            )(info=info).load(root.pk)

        return resolver
