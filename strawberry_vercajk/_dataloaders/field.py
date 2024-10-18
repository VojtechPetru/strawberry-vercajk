import typing
from typing import TYPE_CHECKING, Any

import django.db.models
import strawberry.django

if TYPE_CHECKING:
    from django.db.models.fields.related import RelatedField  # pragma: nocover
    from strawberry_django.fields.field import StrawberryDjangoField  # pragma: nocover


__all__ = [
    "auto_dataloader_field",
]


class UnsupportedRelationError(Exception):
    pass


def get_dataloader_resolver(
    root: "django.db.models.Model",
    info: "strawberry.Info",
) -> typing.Callable[[typing.Any, strawberry.Info], typing.Any]:
    from strawberry_vercajk._dataloaders import (
        M2MDataLoaderFactory,
        PKDataLoaderFactory,
        ReverseFKDataLoaderFactory,
    )

    field_data: StrawberryDjangoField = info._field  # noqa: SLF001
    relation: RelatedField = root._meta.get_field(field_name=field_data.django_name)  # noqa: SLF001
    if relation.one_to_one:
        if isinstance(relation, django.db.models.OneToOneRel):
            return ReverseFKDataLoaderFactory.as_resolver()(root, info)
        return PKDataLoaderFactory.as_resolver()(root, info)
    if relation.many_to_one:
        return PKDataLoaderFactory.as_resolver()(root, info)
    if relation.one_to_many:
        return ReverseFKDataLoaderFactory.as_resolver()(root, info)
    if relation.many_to_many:
        return M2MDataLoaderFactory.as_resolver()(root, info)
    raise UnsupportedRelationError(f"Unsupported relation on {relation.__repr__()}.")


def auto_dataloader_field(
    resolver: typing.Callable[
        ["django.db.models.Model", strawberry.Info],
        typing.Callable[[typing.Any, strawberry.Info], typing.Any],
    ] = get_dataloader_resolver,
    *,
    name: str | None = None,
    field_name: str | None = None,
    default: typing.Any = strawberry.UNSET,  # noqa: ANN401
    **kwargs,
) -> Any:  # noqa: ANN401
    """
    A field which has automatic dataloader resolver based on the relationship type (one-to-one, one-to-many, etc.).

    Example:
    -------
        CONSIDER DJANGO MODELS:
            class Fruit(BaseTestModel):
                plant = models.OneToOneField("FruitPlant", ...)
                color = models.ForeignKey("Color", related_name="fruits", ...)
                varieties = models.ManyToManyField("FruitVariety", related_name="fruits")

            class FruitEater(BaseTestModel):
                favourite_fruit = models.ForeignKey("Fruit", related_name="eaters", ...)

        DEFINE THE STRAWBERRY TYPE AS:
            @strawberry_django.type(models.Fruit)
            class FruitTypeAutoDataLoaderFields:
                plant: FruitPlantType = fields.auto_dataloader_field()
                color: ColorType = fields.auto_dataloader_field()
                varieties: list[FruitVarietyType] = fields.auto_dataloader_field()
                eaters: list[FruitEaterType] = fields.auto_dataloader_field()

    """
    return strawberry.django.field(
        resolver=resolver,
        name=name,
        field_name=field_name,
        default=default,
        **kwargs,
    )
