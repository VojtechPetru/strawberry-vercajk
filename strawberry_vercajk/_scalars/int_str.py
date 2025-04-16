import typing

import strawberry

__all__ = ("IntStr",)


def _scalar_serialize(value: typing.Any) -> int | str:  # noqa: ANN401
    if isinstance(value, int | str):
        return value
    raise TypeError("The value needs to be an integer or a string.")


IntStr = strawberry.scalar(
    typing.NewType("IntStr", int | str),
    name="IntStr",
    serialize=_scalar_serialize,
    parse_value=_scalar_serialize,
    description="An integer or a string.",
)
