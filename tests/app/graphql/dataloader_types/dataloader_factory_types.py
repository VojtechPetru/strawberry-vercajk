import strawberry
import strawberry.django

import strawberry_vercajk
from strawberry_vercajk._dataloaders import PKDataLoaderFactory, ReverseFKDataLoaderFactory, M2MDataLoaderFactory
from tests.app import models
from tests.app.graphql.types import FruitEaterSortEnum, FruitEaterFilterSet


@strawberry.django.type(models.Color)
class ColorTypeDataLoaderFactories:
    """Uses dataloader factories."""

    id: int
    name: str

    @strawberry.field
    def fruits(self: "models.Color", info: "strawberry.Info") -> list["FruitTypeDataLoaderFactories"]:
        loader = PKDataLoaderFactory.make(model=models.Fruit)
        return loader(info=info).load(self.pk)


@strawberry.django.type(models.FruitEater)
class FruitEaterTypeDataLoaderFactories:
    """Uses dataloader factories."""

    id: int
    name: str

    @strawberry.field
    def favourite_fruit(self: "models.FruitEater", info: "strawberry.Info") -> "FruitTypeDataLoaderFactories|None":
        loader = PKDataLoaderFactory.make(model=models.Fruit)
        return loader(info=info).load(self.favourite_fruit_id)

'AppFruitPKDataLoader'
@strawberry.django.type(models.FruitPlant)
class FruitPlantDataLoaderFactoriesType:
    """Uses dataloader factories."""

    id: int
    name: str

    @strawberry.field
    def fruit(self: "models.FruitPlant", info: "strawberry.Info") -> "FruitTypeDataLoaderFactories|None":
        loader = ReverseFKDataLoaderFactory.make(field_descriptor=models.FruitPlant.fruit)
        return loader(info=info).load(self.pk)


@strawberry.django.type(models.FruitVariety)
class FruitVarietyDataLoaderFactoriesType:
    """Uses dataloader factories."""

    id: int
    name: str

    @strawberry.field
    def fruits(self: "models.FruitVariety", info: "strawberry.Info") -> list["FruitTypeDataLoaderFactories"]:
        loader = M2MDataLoaderFactory.make(field_descriptor=models.Fruit.varieties, query_origin=models.FruitVariety)
        return loader(info=info).load(self.pk)


@strawberry.django.type(models.Fruit)
class FruitTypeDataLoaderFactories:
    """Uses dataloader factories."""

    id: int
    name: str

    @strawberry.field
    def color(self: "models.Fruit", info: "strawberry.Info") -> ColorTypeDataLoaderFactories | None:
        loader = PKDataLoaderFactory.make(model=models.Color)
        return loader(info=info).load(self.color_id)

    @strawberry.field
    def plant(self: "models.Fruit", info: "strawberry.Info") -> FruitPlantDataLoaderFactoriesType | None:
        loader = PKDataLoaderFactory.make(model=models.FruitPlant)
        return loader(info=info).load(self.plant_id)

    @strawberry.field
    def eaters(self: "models.Fruit", info: "strawberry.Info") -> list[FruitEaterTypeDataLoaderFactories]:
        loader = ReverseFKDataLoaderFactory.make(field_descriptor=models.FruitEater.favourite_fruit)
        return loader(info=info).load(self.pk)

    @strawberry.field
    def eaters_with_params(
            self: "models.Fruit",
            info: "strawberry.Info",
            page: "strawberry_vercajk.PageInput|None" = strawberry.UNSET,
            sort: "strawberry_vercajk.SortInput[FruitEaterSortEnum]|None" = strawberry.UNSET,
            filters: strawberry_vercajk.pydantic_to_input_type(FruitEaterFilterSet) | None = strawberry.UNSET,
    ) -> list[FruitEaterTypeDataLoaderFactories]:
        filters.clean()
        loader = ReverseFKDataLoaderFactory.make(
            field_descriptor=models.FruitEater.favourite_fruit,
            page=page,
            sort=sort,
            filterset=filters.clean_data,
        )
        return loader(info=info).load(self.pk)

    @strawberry.field
    def varieties(self: "models.Fruit", info: "strawberry.Info") -> list[FruitVarietyDataLoaderFactoriesType]:
        loader = M2MDataLoaderFactory.make(
            field_descriptor=models.Fruit.varieties,
            query_origin=models.Fruit,
        )
        return loader(info=info).load(self.pk)
