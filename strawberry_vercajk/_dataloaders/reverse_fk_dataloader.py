import typing
from collections import defaultdict

import strawberry
from django.db.models import ForeignKey, Model, QuerySet
from django.db.models.fields.related_descriptors import ReverseManyToOneDescriptor, ReverseOneToOneDescriptor

from strawberry_vercajk._dataloaders import core

if typing.TYPE_CHECKING:
    from django.db.models.options import Options
    from strawberry_django.fields.field import StrawberryDjangoField


def _get_related_field(field_descriptor: "ReverseManyToOneDescriptor | ReverseOneToOneDescriptor") -> "ForeignKey":
    """
    Get the related field of the reverse FK relationship, i.e., the ForeignKey/OneToOneField field where
    the relationship is defined.
    """
    if isinstance(field_descriptor, ReverseOneToOneDescriptor):
        return field_descriptor.related.field
    return field_descriptor.field


class ReverseFKDataLoaderClassKwargs(typing.TypedDict):
    field_descriptor: "ReverseManyToOneDescriptor | ReverseOneToOneDescriptor"


class ReverseFKDataLoader(core.BaseDataLoader):
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

    Config: typing.ClassVar[ReverseFKDataLoaderClassKwargs]

    def load_fn(self, keys: list[int]) -> list[list[Model]] | list[Model]:
        field = _get_related_field(self.Config["field_descriptor"])
        model: type[Model] = field.model
        reverse_path: str = field.attname

        qs = model.objects.filter(**{f"{reverse_path}__in": keys})
        # ensure that instances are ordered the same way as input 'ids'
        return self._get_results(qs=qs, keys=keys)

    @classmethod
    def _get_results(
        cls,
        qs: QuerySet,
        keys: list[int],
    ) -> list[list[Model]] | list[Model]:
        reverse_path: str = _get_related_field(cls.Config["field_descriptor"]).attname
        if cls.is_one_to_one():
            key_to_instance: dict[int, Model] = {getattr(instance, reverse_path): instance for instance in qs}
            return [key_to_instance.get(key) for key in keys]

        key_to_instances: dict[int, list[Model]] = defaultdict(list)
        for instance in qs:
            key_to_instances[getattr(instance, reverse_path)].append(instance)
        return [key_to_instances.get(id_, []) for id_ in keys]

    @classmethod
    def is_one_to_one(cls) -> bool:
        """Whether the relationship is reverse relation of one-to-one."""
        return isinstance(cls.Config["field_descriptor"], ReverseOneToOneDescriptor)


class ReverseFKDataLoaderFactory(core.BaseDataLoaderFactory[ReverseFKDataLoader]):
    """
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

    loader_class = ReverseFKDataLoader

    @classmethod
    def make(
            cls,
            *,
            config: ReverseFKDataLoaderClassKwargs,
            _ephemeral: bool = False,
    ) -> type[ReverseFKDataLoader]:
        return super().make(config=config)

    @classmethod
    def generate_loader_name(cls, config: ReverseFKDataLoaderClassKwargs) -> str:
        field = _get_related_field(config["field_descriptor"])
        model: type[Model] = field.model
        meta: Options = model._meta  # noqa: SLF001
        return (
            f"{meta.app_label.capitalize()}"
            f"{meta.object_name}"
            f"{field.attname.capitalize()}"
            f"{cls.loader_class.__name__}"
        )

    @classmethod
    def as_resolver(cls) -> typing.Callable[[typing.Any, strawberry.Info], typing.Any]:
        # the first arg needs to be called 'root'
        def resolver(root: "Model", info: "strawberry.Info") -> typing.Any:  # noqa: ANN401
            field_data: StrawberryDjangoField = info._field  # noqa: SLF001
            model: type[Model] = root._meta.model  # noqa: SLF001
            field_descriptor: ReverseManyToOneDescriptor = getattr(model, field_data.django_name)
            return cls.make(config={"field_descriptor": field_descriptor})(info=info).load(root.pk)

        return resolver
