import typing

import factory

from tests.app import models
if typing.TYPE_CHECKING:
    import django.db.models

DEFAULT_FRUIT_VARIETIES_COUNT: int = 5
DEFAULT_FRUIT_EATERS_COUNT: int = 4


class TypedDjangoModelFactory[T: "django.db.models.Model"](factory.django.DjangoModelFactory):
    create: typing.Callable[..., T]
    create_batch: typing.Callable[..., list[T]]


class ColorFactory(TypedDjangoModelFactory[models.Color]):
    class Meta:
        model = models.Color

    name = factory.Faker("word")


class FruitPlantFactory(TypedDjangoModelFactory[models.FruitPlant]):
    class Meta:
        model = models.FruitPlant

    name = factory.Faker("word")


class FruitVarietyFactory(TypedDjangoModelFactory[models.FruitVariety]):
    class Meta:
        model = models.FruitVariety

    name = factory.Faker("word")


class FruitFactory(TypedDjangoModelFactory[models.Fruit]):
    class Meta:
        model = models.Fruit

    name = factory.Faker("word")
    color = factory.SubFactory(ColorFactory)
    plant = factory.SubFactory(FruitPlantFactory)

    @classmethod
    def create(
            cls,
            with_varieties: bool = False,
            with_eaters: bool = False,
            **kwargs,
    ) -> models.Fruit:
        if with_varieties:
            kwargs["varieties"] = FruitVarietyFactory.create_batch(DEFAULT_FRUIT_VARIETIES_COUNT)
        instance = super().create(**kwargs)
        if with_eaters:
            FruitEaterFactory.create_batch(DEFAULT_FRUIT_EATERS_COUNT, favourite_fruit=instance)
        return instance

    @classmethod
    def create_batch(
            cls,
            size: int,
            *,
            with_varieties: bool = False,
            with_eaters: bool = False,
            **kwargs,
    ) -> list[models.Fruit]:
        return super().create_batch(
            size,
            with_varieties=with_varieties,
            with_eaters=with_eaters,
            **kwargs
        )

    @factory.post_generation
    def varieties(
        self: models.Fruit,
        create: bool,
        extracted: typing.Iterable["models.FruitVariety"],
    ) -> None:
        if not create or not extracted:
            # Simple build, or nothing to add, do nothing.
            return
        self.varieties.add(*extracted)


class FruitEaterFactory(TypedDjangoModelFactory[models.FruitEater]):
    class Meta:
        model = models.FruitEater

    name = factory.Faker("word")
    favourite_fruit = factory.SubFactory(FruitFactory)
