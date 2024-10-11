import strawberry

__all__ = [
    "ColorType",
    "FruitType",
    "FruitVarietyType",
    "FruitPlantType",
    "FruitEaterType",
]


@strawberry.type
class FruitType:
    id: int
    name: str
    color: "ColorType|None"
    plant: "FruitPlantType|None"
    varieties: list["FruitVarietyType"]
    eaters: list["FruitEaterType"]


@strawberry.type
class FruitVarietyType:
    id: int
    name: str
    fruits: list["FruitType"]


@strawberry.type
class FruitPlantType:
    id: int
    name: str
    fruit: FruitType | None


@strawberry.type
class ColorType:
    id: int
    name: str
    fruits: list[FruitType]


@strawberry.type
class FruitEaterType:
    id: int
    name: str
    favourite_fruit: FruitType | None
