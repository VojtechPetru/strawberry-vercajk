__all__ = [
    "FKDataLoader",
]

import abc
import typing

import strawberry
from strawberry_vercajk._dataloaders import core


class FKDataLoader[K: typing.Hashable, R](core.BaseDataLoader[K, R]):  # TODO test
    """
    Base loader for reversed FK relationship (e.g., BlogPosts of a User).

    WARNING: This dataloader fetches *all* related objects for a given list of parent objects.
    If you need to e.g. paginate, filter, or sort the related objects, use FKListDataLoader instead.

    EXAMPLE - load blog posts of an account:
        FOR THE FOLLOWING DJANGO MODEL:
            class User(models.Model):
                ...

            class BlogPost(models.Model):
                published_by = models.ForeignKey("User", related_name="blog_posts", ...)

        1. DATALOADER DEFINITION
        class UserBlogPostsFKDataLoader(FKDataLoader):
            load_fn = get_blog_posts_by_user_ids


        2. USAGE
        @strawberry.type(models.User)
        class UserType:
            ...

            @strawberry.field
            def blog_posts(self: "models.User", info: "Info") -> list["BlogPostType"]:
                return UserBlogPostsFKDataLoader(info=info).load(self.pk)
    """

    @property
    @abc.abstractmethod
    def load_fn(self) -> typing.Callable[[list[K]], dict[K, list[R]]]: ...

    def __init__(
        self,
        info: strawberry.Info,
        *,
        one_to_one: bool = False,
    ) -> None:
        self.one_to_one = one_to_one
        super().__init__(info=info)

    def process_results(self, keys: list[K], results: typing.Mapping[K, list[R]]) -> list[list[R]] | list[R]:
        if self.one_to_one:
            return [results.get(key, [None])[0] for key in keys]
        return [results.get(key, []) for key in keys]


# TODO implement in Django-specific package
# class ReverseFKDataLoaderFactory(core.BaseDataLoaderFactory[FKDataLoader]):
#     """
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
#     loader_class = FKDataLoader
#
#     @classmethod
#     def generate_loader_name(cls) -> str:
#         field = _get_related_field(config["field_descriptor"])
#         model: type[Model] = field.model
#         meta: Options = model._meta
#         return (
#             f"{meta.app_label.capitalize()}"
#             f"{meta.object_name}"
#             f"{field.attname.capitalize()}"
#             f"{cls.loader_class.__name__}"
#         )
#
#     @classmethod
#     def as_resolver(cls) -> typing.Callable[[typing.Any, strawberry.Info], typing.Any]:
#         # the first arg needs to be called 'root'
#         def resolver(root: "Model", info: "strawberry.Info") -> typing.Any:
#             def _load_fn(keys: list[int]) -> dict[int, list["Model"]]:
#                 if isinstance(field_descriptor, ReverseOneToOneDescriptor):
#                     field: ForeignKey = field_descriptor.related.field
#                 else:
#                     field = field_descriptor.field
#                 model: type[Model] = field.model
#                 reverse_path: str = field.attname
#                 qs = model.objects.filter(**{f"{reverse_path}__in": keys}).order_by()
#
#                 ret: dict[int, list[Model]] = defaultdict(list)
#                 for instance in qs:
#                     ret[getattr(instance, reverse_path)].append(instance)
#                 return dict(ret)
#
#             field_data: StrawberryDjangoField = info._field
#             model: type[Model] = root._meta.model
#             field_descriptor: ReverseManyToOneDescriptor | ReverseOneToOneDescriptor = getattr(
#               model,
#               field_data.django_name
#             )
#             return cls.make()(
#                 load_fn=_load_fn,
#                 info=info,
#                 one_to_one=isinstance(field_descriptor, ReverseOneToOneDescriptor),
#             ).load(root.pk)
#
#         return resolver
