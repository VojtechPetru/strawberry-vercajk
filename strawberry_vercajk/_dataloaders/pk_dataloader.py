__all__ = [
    "PKDataLoader",
]

import abc
import typing

from strawberry_vercajk._dataloaders import core


class ResultType(typing.Protocol):
    pk: typing.Any


class PKDataLoader[K: typing.Hashable, R: ResultType](core.BaseDataLoader[K, R]):  # TODO test
    """
    Base loader to load objects by their primary key.

    EXAMPLE - load Alliance of Account:
        1. DATALOADER DEFINITION
        class PKAllianceDataLoader(PKDataLoader):
            load_fn = get_alliances_by_ids

        2. USAGE
        @strawberry.type(models.Account)
        class AccountType:
            ...

            @strawberry.field
            def alliance(self: "models.Account", info: "Info") -> list["Alliance"]:
                return PKAllianceDataLoader(info=info).load(self.alliance_id)

    """

    @property
    @abc.abstractmethod
    def load_fn(self) -> typing.Callable[[list[K]], list[R]]: ...

    @typing.override
    def process_results(self, keys: list[K], results: list[R]) -> list[R]:
        key__res: dict[K, R] = {r.pk: r for r in results}
        # ensure results are ordered in the same way as input keys
        return [key__res.get(id_) for id_ in keys]


# class PKDataLoaderFactory(core.BaseDataLoaderFactory[PKDataLoader]):  # TODO reimplement in Django-specific package
#     """
#     Base factory for simple PK relationship dataloaders. For example, get favourite fruit (Fruit model) of a User.
#
#     Example:
#     -------
#         CONSIDER DJANGO MODELS:
#             class Fruit(models.Model):
#                 ...
#
#             class User(models.Model):
#                 favourite_fruit = models.ForeignKey("Fruit", ...)
#
#         THE FACTORY WOULD BE USED IN THE FOLLOWING MANNER:
#             @strawberry.django.type(models.User)
#             class UserType:
#                 ...
#                 @strawberry.field
#                 def favourite_fruit(self: "models.User", info: "Info") -> "FruitType":
#                     loader = PKDataLoaderFactory.make('<django_app>.Fruit')
#                     return loader(context=info.context).load(self.favourite_fruit_id)
#
#     """
#
#     loader_class = PKDataLoader
#
#     @classmethod
#     def generate_loader_name(cls) -> str:
#         return f"{model_cls._meta.app_label.capitalize()}{model_cls._meta.object_name}{cls.loader_class.__name__}"
#
#     @classmethod
#     def as_resolver(cls) -> typing.Callable[[typing.Any, strawberry.Info], typing.Any]:
#         # the first arg needs to be called 'root'
#         def resolver(root: "django.db.models.Model", info: "strawberry.Info") -> typing.Any:
#             def _load_fn(keys: list[int]) -> list["django.db.models.Model"]:
#                 return list(dj_model.objects.filter(pk__in=keys).order_by())
#
#             field_data: StrawberryDjangoField = info._field
#             relation: RelatedField = root._meta.get_field(field_name=field_data.django_name)
#             pk: int = getattr(root, relation.attname)
#             dj_model: type[django.db.models.Model] = relation.related_model
#             return cls.make()(load_fn=_load_fn, info=info).load(pk)
#
#         return resolver
