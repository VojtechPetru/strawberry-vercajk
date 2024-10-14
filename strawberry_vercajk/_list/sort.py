import dataclasses
import enum
import functools
import typing

import django.core.exceptions
import strawberry

from strawberry_vercajk._base import utils as base_utils

if typing.TYPE_CHECKING:
    import django.db.models.Model

__all__ = [
    "OrderingDirection",
    "FieldSortEnum",
    "model_sort_enum",
]

_SORT_MODEL_ATTR_NAME: typing.LiteralString = "__VERCAJK_MODEL"


def model_sort_enum[T: "FieldSortEnum"](
    model: type["django.db.models.Model"],
) -> typing.Callable[[type[T]], type[T]]:
    @functools.wraps(model_sort_enum)
    def wrapper(
        sort_enum_class: type[T],
    ) -> type[T]:
        if not issubclass(sort_enum_class, FieldSortEnum):
            raise TypeError(f"`{sort_enum_class.__name__}` must be a subclass of `{FieldSortEnum.__name__}`.")

        if hasattr(sort_enum_class, _SORT_MODEL_ATTR_NAME):
            # Seems like an edge case. Decide what to do if this happens, maybe namespace the attribute better.
            raise ValueError(f"`{_SORT_MODEL_ATTR_NAME}` is already set for `{sort_enum_class.__name__}`.")
        setattr(sort_enum_class, _SORT_MODEL_ATTR_NAME, model)
        sort_enum_class._initialize()  # noqa: SLF001
        return sort_enum_class

    return wrapper


class OrderingDirection(enum.Enum):
    ASC = strawberry.enum_value("ASC", description="Ascending order, i.e. 1, 2, 3... or a, b, c...")
    DESC = strawberry.enum_value("DESC", description="Descending order, i.e. 3, 2, 1... or c, b, a...")

    @property
    def is_asc(self) -> bool:
        return self == OrderingDirection.ASC

    @property
    def is_desc(self) -> bool:
        return self == OrderingDirection.DESC


class FieldSortEnum(enum.Enum):
    @classmethod
    def _initialize(cls) -> None:
        for sort_enum in cls:
            sort_enum: cls
            cls._check_field_exists(sort_value=sort_enum.value)

    @classmethod
    def get_django_model(cls) -> type["django.db.models.Model"]:
        """Django database model for this sort enum. It is set by the `model_sort_enum` decorator."""
        if not hasattr(cls, _SORT_MODEL_ATTR_NAME):
            raise ImproperlyInitializedFieldSortEnumError(cls)
        return getattr(cls, _SORT_MODEL_ATTR_NAME)

    @classmethod
    def _check_field_exists(cls, sort_value: str) -> None:
        """Checks if the field exists on the model."""
        base_utils.check_django_field_exists(cls.get_django_model(), sort_value)


@dataclasses.dataclass
class ImproperlyInitializedFieldSortEnumError(Exception):
    sort_enum_cls: type[FieldSortEnum]

    def __str__(self) -> str:
        return (
            f"`{self.sort_enum_cls.__name__}` is not properly initialized. "
            f"Did you forget to use `@{model_sort_enum.__name__}` decorator on it?"
        )
