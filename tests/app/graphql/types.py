import typing

import strawberry
import strawberry.django

__all__ = [
    "ColorType",
    "FruitType",
    "FruitVarietyType",
    "FruitPlantType",
    "FruitEaterType",
    "FruitEaterSortEnum",
    "FruitEaterFilterSet",
]

import strawberry_vercajk
from tests.app import models
from tests.app.models import FruitPlant


@strawberry_vercajk.model_sort_enum(models.FruitEater)
class FruitEaterSortEnum(strawberry_vercajk.FieldSortEnum):
    ID = "id"
    NAME = "name"
    FAVOURITE_FRUIT_NAME = "favourite_fruit__name"


@strawberry_vercajk.model_filter(models.FruitEater)
class FruitEaterFilterSet(strawberry_vercajk.FilterSet):
    name: typing.Annotated[
        str | None,
        strawberry_vercajk.Filter(
            model_field="name",
            lookup="icontains",
        ),
    ] = None


@strawberry.django.type(models.Fruit)
class FruitType:
    id: int
    name: str
    color: "ColorType|None"
    plant: "FruitPlantType|None"
    varieties: list["FruitVarietyType"]
    eaters: list["FruitEaterType"]


@strawberry.django.type(models.FruitVariety)
class FruitVarietyType:
    id: int
    name: str
    fruits: list["FruitType"]


@strawberry.django.type(FruitPlant)
class FruitPlantType:
    id: int
    name: str
    fruit: FruitType | None


@strawberry.django.type(models.Color)
class ColorType:
    id: int
    name: str
    fruits: list[FruitType]


@strawberry.django.type(models.FruitEater)
class FruitEaterType:
    id: int
    name: str
    favourite_fruit: FruitType | None
