import strawberry
import strawberry.django

from strawberry_vercajk._dataloaders import auto_dataloader_field
from tests.app import models


@strawberry.django.type(models.Color)
class ColorAutoDataLoaderType:
    id: int
    name: str
    fruits: list["FruitAutoDataLoaderType"] = auto_dataloader_field()


@strawberry.django.type(models.FruitPlant)
class FruitPlantAutoDataLoaderType:
    id: int
    name: str
    fruit: "FruitAutoDataLoaderType|None" = auto_dataloader_field()


@strawberry.django.type(models.FruitVariety)
class FruitVarietyAutoDataLoaderType:
    id: int
    name: str
    fruits: list["FruitAutoDataLoaderType"] = auto_dataloader_field()


@strawberry.django.type(models.FruitEater)
class FruitEaterAutoDataLoaderType:
    id: int
    name: str
    favourite_fruit: "FruitAutoDataLoaderType|None" = auto_dataloader_field()


@strawberry.django.type(models.Fruit)
class FruitAutoDataLoaderType:
    """Uses auto dataloader fields."""
    id: int
    name: str
    color: "ColorAutoDataLoaderType|None" = auto_dataloader_field()
    plant: "FruitPlantAutoDataLoaderType|None" = auto_dataloader_field()
    varieties: list[FruitVarietyAutoDataLoaderType] = auto_dataloader_field()
    eaters: list[FruitEaterAutoDataLoaderType] = auto_dataloader_field()
