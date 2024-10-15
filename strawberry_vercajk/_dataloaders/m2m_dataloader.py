import typing
from collections import defaultdict

import django.db.models
import strawberry

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
        through_model = self.get_through_model()
        through_model_query_origin_field, through_model_target_field = self.get_through_model_fields()

        through_ids: list[tuple[int, int]] = list(
            through_model.objects.filter(
                **{f"{through_model_query_origin_field}__in": keys},
            )
            .order_by()
            .values_list(through_model_query_origin_field, through_model_target_field),
        )

        target_qs = self.query_target().objects.filter(pk__in={target_id for _, target_id in through_ids}).order_by()

        # mapping of which targets are connected to which keys
        target_to_keys: dict[int, list[int]] = defaultdict(list)
        for origin_id, target_id in through_ids:
            target_to_keys[target_id].append(origin_id)
        target_to_keys = dict(target_to_keys)

        # For each target, get the keys it "belongs" to, fill the list with targets for each such key
        # and return them in the same order as the input keys.
        key_to_targets: dict[int, list[django.db.models.Model]] = defaultdict(list)
        for target in target_qs:
            for key in target_to_keys.get(target.pk, []):
                key_to_targets[key].append(target)
        return [key_to_targets[key] for key in keys]

    @classmethod
    def query_target(cls) -> type[django.db.models.Model]:
        field: django.db.models.ManyToManyField = cls.Config["field_descriptor"].field
        model_query_origin = cls.Config["query_origin"]
        return field.model if model_query_origin == field.related_model else field.related_model

    @classmethod
    def get_through_model_fields(cls) -> tuple[str, str]:
        model_query_origin = cls.Config["query_origin"]
        model_query_target = cls.query_target()

        query_origin_field_candidates = cls._get_through_model_field(model_query_origin)
        query_target_field_candidates = cls._get_through_model_field(model_query_target)

        if len(query_origin_field_candidates) == 1 and len(query_target_field_candidates) == 1:
            return query_origin_field_candidates[0], query_target_field_candidates[0]

        # TODO if we get here - will need to handle through_fields
        raise ValueError(
            f"Could not find through fields for `{model_query_origin.__name__}` and `{model_query_target.__name__}`."
            f" Found: {query_origin_field_candidates} and {query_target_field_candidates}.",
        )

    @classmethod
    def _get_through_model_field(cls, model: type[django.db.models.Model]) -> list[str]:
        """
        Get fields on the through model that point to the given model.
        """
        through_model = cls.get_through_model()
        field_candidates: list[str] = []
        for through_model_field in through_model._meta.get_fields():  # noqa: SLF001
            if not isinstance(through_model_field, django.db.models.ForeignKey):
                continue

            through_model_field: django.db.models.ForeignKey
            if through_model_field.related_model != model:
                continue

            field_candidates.append(through_model_field.attname)  # django.db.models.ManyToManyRel
        return field_candidates


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
