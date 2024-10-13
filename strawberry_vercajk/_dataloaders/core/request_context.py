import dataclasses
import typing

import strawberry
from strawberry.django.context import StrawberryDjangoContext

if typing.TYPE_CHECKING:
    from strawberry_vercajk._dataloaders import BaseDataLoader


__all__ = [
    "DataloadersContext",
]

@dataclasses.dataclass
class DataloadersContext(StrawberryDjangoContext):
    dataloaders: dict[type["BaseDataLoader"], "BaseDataLoader"] = strawberry.field(default_factory=dict)
