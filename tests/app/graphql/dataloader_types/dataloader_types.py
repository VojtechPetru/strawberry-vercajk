import strawberry
import strawberry.django

from strawberry_vercajk._dataloaders import PKDataLoader, ReverseFKDataLoader, M2MDataLoader
from tests.app import models


class FruitDataLoader(PKDataLoader):
    model = models.Fruit


class ColorPKDataLoader(PKDataLoader):
    model = models.Color


class FruitReverseOneToOneDataLoader(ReverseFKDataLoader):
    field_descriptor = models.FruitPlant.fruit


class FruitPlantPKDataLoader(PKDataLoader):
    model = models.FruitPlant


class FruitEatersReverseFKDataLoader(ReverseFKDataLoader):
    field_descriptor = models.FruitEater.favourite_fruit


class FruitPlantFruitReverseOneToOneDataLoader(ReverseFKDataLoader):
    field_descriptor = models.Fruit.plant


class FruitVarietiesM2MDataLoader(M2MDataLoader):
    field_descriptor = models.Fruit.varieties
    query_origin = models.Fruit  # from which model of the two is the query originated


class FruitVarietyFruitsM2MDataLoader(M2MDataLoader):
    field_descriptor = models.Fruit.varieties
    query_origin = models.FruitVariety  # from which model of the two is the query originated


@strawberry.django.type(models.Color)
class ColorTypeDataLoadersType:
    """Uses the simplest form of dataloaders."""

    id: int
    name: str

    @strawberry.field
    def fruits(self: "models.Color", info: "strawberry.Info") -> list["FruitTypeDataLoaders"]:
        return ColorPKDataLoader(context=info.context).load(self.pk)


@strawberry.django.type(models.FruitEater)
class FruitEaterDataLoadersType:
    """Uses the simplest form of dataloaders."""

    id: int
    name: str

    @strawberry.field
    def favourite_fruit(self: "models.FruitEater", info: "strawberry.Info") -> "FruitTypeDataLoaders|None":
        return FruitDataLoader(context=info.context).load(self.favourite_fruit_id)


@strawberry.django.type(models.FruitPlant)
class FruitPlantDataLoadersType:
    """Uses the simplest form of dataloaders."""

    id: int
    name: str

    @strawberry.field
    def fruit(self: "models.FruitPlant", info: "strawberry.Info") -> "FruitTypeDataLoaders|None":
        return FruitReverseOneToOneDataLoader(context=info.context).load(self.pk)


@strawberry.django.type(models.FruitVariety)
class FruitVarietyDataLoadersType:
    """Uses the simplest form of dataloaders."""

    id: int
    name: str

    @strawberry.field
    def fruits(self: "models.FruitVariety", info: "strawberry.Info") -> list["FruitTypeDataLoaders"]:
        return FruitVarietyFruitsM2MDataLoader(context=info.context).load(self.pk)


@strawberry.django.type(models.Fruit)
class FruitTypeDataLoaders:
    """Uses the simplest form of dataloaders."""

    id: int
    name: str

    @strawberry.field
    def color(self: "models.Fruit", info: "strawberry.Info") -> ColorTypeDataLoadersType | None:
        return ColorPKDataLoader(context=info.context).load(self.color_id)

    @strawberry.field
    def plant(self: "models.Fruit", info: "strawberry.Info") -> FruitPlantDataLoadersType | None:
        return FruitPlantPKDataLoader(context=info.context).load(self.plant_id)

    @strawberry.field
    def eaters(self: "models.Fruit", info: "strawberry.Info") -> list[FruitEaterDataLoadersType]:
        return FruitEatersReverseFKDataLoader(context=info.context).load(self.pk)

    @strawberry.field
    def varieties(self: "models.Fruit", info: "strawberry.Info") -> list[FruitVarietyDataLoadersType]:
        return FruitVarietiesM2MDataLoader(context=info.context).load(self.pk)
