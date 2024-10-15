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
from strawberry_vercajk import ListRespHandler
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

    @strawberry.field
    def eaters_with_params(
            self: "models.Fruit",
            info: "strawberry.Info",
            page: "strawberry_vercajk.PageInput|None" = strawberry.UNSET,
            sort: "strawberry_vercajk.SortInput[FruitEaterSortEnum]|None" = strawberry.UNSET,
            filters: strawberry_vercajk.pydantic_to_input_type(FruitEaterFilterSet) = strawberry.UNSET,
    ) -> strawberry_vercajk.ListInnerType["FruitEaterType"]:
        filters.clean()
        qs = models.FruitEater.objects.filter(favourite_fruit_id=self.pk)
        handler = strawberry_vercajk.ListRespHandler(qs, info)
        qs = handler.apply_filters(qs, filters.clean_data)
        qs = handler.apply_sorting(qs, sort)
        qs_page = handler.apply_pagination(qs, page)
        items_count = qs_page.items_count
        return strawberry_vercajk.ListInnerType[FruitEaterType](
            pagination=strawberry_vercajk.PageInnerMetadataType(
                current_page=page.page_number,
                page_size=page.page_size,
                items_count=items_count,
                has_next_page=qs_page.has_next(),
                has_previous_page=qs_page.has_previous(),
            ),
            items=qs_page.object_list,
        )


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
