import typing
from collections import defaultdict

import django.db.models
import strawberry
from django.db.models import F

from strawberry_vercajk._dataloaders import core

if typing.TYPE_CHECKING:
    from django.db.models.fields.related_descriptors import ManyToManyDescriptor
    from django.db.models.options import Options
    from strawberry_django.fields.field import StrawberryDjangoField


class M2MDataLoaderClassKwargs(typing.TypedDict):
    field_descriptor: "ManyToManyDescriptor"
    query_origin: type[django.db.models.Model]


class M2MDataLoader(core.BaseDataLoader):
    """
    Base loader for M2M relationship (e.g., Workplace of a User).

    EXAMPLE - load workplaces of a user:
        1. DATALOADER DEFINITION
        class UserWorkplacesM2MDataLoader(M2MDataLoader):
            field_descriptor = User.workplaces

        2. USAGE
        @strawberry.django.type(models.User)
        class UserType:
            ...

            @strawberry.field
            def workplaces(self: "models.User", info: "Info") -> list["WorkplaceType"]:
                return UserWorkplacesM2MDataLoader(context=info.context).load(self.pk)
    """

    Config: typing.ClassVar[M2MDataLoaderClassKwargs]

    @classmethod
    def get_through_model(cls) -> type[django.db.models.Model]:
        """Returns the through model of this m2m relationship."""
        return cls.Config["field_descriptor"].rel.through

    def load_fn(self, keys: list[int]) -> list[list[django.db.models.Model]]:
        """
        :param keys: list of ids from the parent model (e.g., if we want to get workplaces of users, keys are user ids)
        """
        key_id_annot: str = "_key_id"
        accessor_name = self.accessor_name()

        target_qs = (
            self.query_target()
            .objects.annotate(
                **{key_id_annot: F(f"{accessor_name}__id")},
            )
            .filter(
                **{f"{key_id_annot}__in": keys},
            )
            .order_by()
        )

        key_to_targets: dict[int, list[django.db.models.Model]] = defaultdict(list)
        for target in target_qs:
            key_to_targets[getattr(target, key_id_annot)].append(target)
        return [key_to_targets[key] for key in keys]

    @classmethod
    def query_target(cls) -> type[django.db.models.Model]:
        field: django.db.models.ManyToManyField = cls.Config["field_descriptor"].field
        model_query_origin = cls.Config["query_origin"]
        return field.model if model_query_origin == field.related_model else field.related_model

    @classmethod
    def accessor_name(cls) -> str:
        descriptor = cls.Config["field_descriptor"]
        query_origin = cls.Config["query_origin"]
        field: django.db.models.ManyToManyField = descriptor.field
        return field.attname if query_origin == field.related_model else descriptor.rel.accessor_name


class M2MDataLoaderFactory(core.BaseDataLoaderFactory[M2MDataLoader]):
    """
    Base factory for M2M relationship dataloaders.
    For example, get Workplaces of a User.

    Example:
    -------
        CONSIDER DJANGO MODELS:
            class User(models.Model):
                workplaces = models.ManyToManyField("Workplace", related_name="users")

            class Workplace(models.Model):
                ...

        THE FACTORY WOULD BE USED IN A FOLLOWING MANNER:
            @strawberry.django.type(models.User)
            class UserType:
                ...
                @strawberry.field
                async def workplaces(self: "models.User", info: "Info") -> list["WorkplaceType"]:
                    loader = M2MDataLoaderFactory.make(User.workplaces)
                    return loader(context=info.context).load(self.pk)

    """

    loader_class = M2MDataLoader

    @classmethod
    def make(
        cls,
        *,
        config: M2MDataLoaderClassKwargs,
        _ephemeral: bool = False,
    ) -> type[M2MDataLoader]:
        return super().make(config=config, _ephemeral=_ephemeral)

    @classmethod
    def generate_loader_name(cls, config: M2MDataLoaderClassKwargs) -> str:
        field: django.db.models.ManyToManyField = config["field_descriptor"].field
        model: type[django.db.models.Model] = field.model
        meta: Options = model._meta  # noqa: SLF001
        return (
            f"{config["query_origin"].__name__}{meta.app_label.capitalize()}{meta.object_name}"
            f"{field.attname.capitalize()}{cls.loader_class.__name__}"
        )

    @classmethod
    def as_resolver(cls) -> typing.Callable[[typing.Any, strawberry.Info], typing.Any]:
        # the first arg needs to be called 'root'
        def resolver(root: "django.db.models.Model", info: "strawberry.Info") -> typing.Any:  # noqa: ANN401
            field_data: StrawberryDjangoField = info._field  # noqa: SLF001
            model: type[django.db.models.Model] = root._meta.model  # noqa: SLF001
            field_descriptor: ManyToManyDescriptor = getattr(model, field_data.django_name)
            return cls.make(
                config={
                    "field_descriptor": field_descriptor,
                    "query_origin": model,
                },
            )(info=info).load(root.pk)

        return resolver
