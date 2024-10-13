import typing

import django.db.models
import strawberry

from strawberry_vercajk._dataloaders import core

if typing.TYPE_CHECKING:
    from django.db.models.fields.related import RelatedField
    from strawberry_django.fields.field import StrawberryDjangoField

__all__ = [
    "PKDataLoader",
    "PKDataLoaderFactory",
]


class PKDataLoader(core.BaseDataLoader):
    """
    Base loader for simple PK relationship (e.g., Alliance of Account).

    EXAMPLE - load Alliance of Account:
        1. DATALOADER DEFINITION
        class PKAllianceDataLoader(PKDataLoader):
            model = Alliance

        2. USAGE
        @strawberry.django.type(models.Account)
        class AccountType:
            ...

            @strawberry.field
            def alliance(self: "models.Account", info: "Info") -> list["Alliance"]:
                return PKAllianceDataLoader(context=info.context).load(self.alliance_id)

    """

    model: typing.ClassVar[type["django.db.models.Model"]] = NotImplemented

    def load_fn(self, keys: list[int]) -> list[django.db.models.Model | None]:
        qs = type(self).model.objects.filter(pk__in=keys).order_by()
        id_to_instance: dict[int, django.db.models.Model] = {instance.pk: instance for instance in qs}
        # ensure instances are ordered in the same way as input 'keys'
        return [id_to_instance.get(id_) for id_ in keys]


class PKDataLoaderFactory(core.BaseDataLoaderFactory[PKDataLoader]):
    """
    Base factory for simple PK relationship dataloaders. For example, get favourite fruit (Fruit model) of a User.

    Example:
    -------
        CONSIDER DJANGO MODELS:
            class Fruit(models.Model):
                ...

            class User(models.Model):
                favourite_fruit = models.ForeignKey("Fruit", ...)

        THE FACTORY WOULD BE USED IN THE FOLLOWING MANNER:
            @strawberry.django.type(models.User)
            class UserType:
                ...
                @strawberry.field
                def favourite_fruit(self: "models.User", info: "Info") -> "FruitType":
                    loader = PKDataLoaderFactory.make('<django_app>.Fruit')
                    return loader(context=info.context).load(self.favourite_fruit_id)

    """

    loader_class = PKDataLoader

    @classmethod
    def make(cls, model: type["django.db.models.Model"]) -> type[PKDataLoader]:
        return super().make(model=model)

    @classmethod
    def get_loader_unique_cls_name(
        cls,
        model: type["django.db.models.Model"],
    ) -> str:
        return f"{model._meta.app_label.capitalize()}{model._meta.object_name}{cls.loader_class.__name__}"  # noqa: SLF001

    @classmethod
    def as_resolver(cls) -> typing.Callable[[typing.Any, strawberry.Info], typing.Any]:
        # the first arg needs to be called 'root'
        def resolver(root: "django.db.models.Model", info: "strawberry.Info") -> typing.Any:  # noqa: ANN401
            field_data: StrawberryDjangoField = info._field  # noqa: SLF001
            relation: RelatedField = root._meta.get_field(field_name=field_data.django_name)  # noqa: SLF001
            pk: int = getattr(root, relation.attname)
            return cls.make(model=field_data.django_model)(context=info.context).load(pk)

        return resolver
