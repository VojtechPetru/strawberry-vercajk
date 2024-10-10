import dataclasses

import strawberry
from strawberry.schema_directive import Location

__all__ = [
    "FieldConstraintsDirective",
]


@dataclasses.dataclass(kw_only=True)
class FieldConstraints:
    gt: int | None = None
    gte: int | None = None
    lt: int | None = None
    lte: int | None = None
    max_length: int | None = None
    min_length: int | None = None
    max_digits: int | None = None
    decimal_places: int | None = None
    pattern: str | None = None
    multiple_of: int | None = None

    def __bool__(self) -> bool:
        return any(
            getattr(self, field.name) is not None
            for field in dataclasses.fields(self)
        )


@strawberry.schema_directive(locations=[Location.INPUT_FIELD_DEFINITION], repeatable=True, name="FieldConstraints")
class FieldConstraintsDirective(FieldConstraints):
    pass
