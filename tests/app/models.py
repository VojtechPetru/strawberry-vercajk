import typing

from django.db import models
if typing.TYPE_CHECKING:
    from django.db.models.fields.related_descriptors import ReverseManyToOneDescriptor, ReverseOneToOneDescriptor


class TestModel(models.Model):
    name: str = models.CharField(max_length=32)

    objects: models.QuerySet

    class Meta:
        abstract = True

    def __str__(self) -> str:
        return self.name


class Fruit(TestModel):
    plant = models.OneToOneField("FruitPlant", on_delete=models.SET_NULL, null=True, related_name="fruit")
    plant_id: int | None
    color = models.ForeignKey("Color", null=True, blank=True, related_name="fruits", on_delete=models.CASCADE)
    color_id: int | None
    varieties = models.ManyToManyField("FruitVariety", related_name="fruits")


class FruitPlant(TestModel):
    fruit: "Fruit|None|ReverseOneToOneDescriptor"


class FruitEater(TestModel):
    favourite_fruit: "Fruit|None|ReverseManyToOneDescriptor" = models.ForeignKey(
        "Fruit",
        null=True,
        on_delete=models.SET_NULL,
        related_name="eaters",
    )
    favourite_fruit_id: int | None


class FruitVariety(TestModel):
    pass


class Color(TestModel):
    pass

