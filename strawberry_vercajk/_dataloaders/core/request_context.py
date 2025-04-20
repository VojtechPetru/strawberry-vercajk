__all__ = [
    "InfoDataloadersContextMixin",
]
import dataclasses
import typing

import strawberry

if typing.TYPE_CHECKING:
    from strawberry_vercajk._dataloaders import BaseDataLoader


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

    dataloaders: dict[type["BaseDataLoader"], "BaseDataLoader"] = strawberry.field(default_factory=dict)  # noqa: RUF009
