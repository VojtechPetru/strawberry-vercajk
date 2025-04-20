__all__ = [
    "DataLoadersExtension",
]

import contextlib
import contextvars
import typing

import strawberry.extensions
if typing.TYPE_CHECKING:
    from strawberry_vercajk import AsyncDataLoader

T = typing.TypeVar("T", bound="BaseAsyncDataLoader")

dataloaders_context_var = contextvars.ContextVar[dict[type[T], T]]("dataloaders_context_var")


@contextlib.contextmanager
def dataloaders_context() -> typing.Iterator[None]:
    token = dataloaders_context_var.set({})
    try:
        yield
    finally:
        dataloaders_context_var.reset(token)



class DataLoadersExtension(strawberry.extensions.SchemaExtension):
    def on_operation(self) -> typing.Iterator[None]:
        with dataloaders_context():
            yield
