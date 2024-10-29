import dataclasses
import typing

import strawberry

if typing.TYPE_CHECKING:
    from strawberry_vercajk._dataloaders import BaseDataLoader


__all__ = [
    "InfoDataloadersContextMixin",
]


@dataclasses.dataclass
class InfoDataloadersContextMixin:
    """
    A mixin to be used with a `strawberry.django.context.StrawberryDjangoContext` to store dataloaders.
    Usage:
    >>> from strawberry.django.context import StrawberryDjangoContext
    ...
    ... @dataclasses.dataclass
    ... class Context(InfoDataloadersContextMixin, StrawberryDjangoContext):
    ...     pass
    """

    dataloaders: dict[int, "BaseDataLoader"] = strawberry.field(default_factory=dict)  # key = loader unique key
