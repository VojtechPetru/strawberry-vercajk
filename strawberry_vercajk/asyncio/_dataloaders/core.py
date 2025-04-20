__all__ = [
    "AsyncDataLoader",
]

import abc
import typing

import strawberry
import strawberry.dataloader


class AsyncDataLoader[K: typing.Hashable, R](strawberry.dataloader.DataLoader[K, R]):
    # serves two purposes:
    # 1. "mark" that the class instance was already created
    # 2. don't allow creating more than one instance of the class (see __init__)
    _instance_cache: type[typing.Self] | None = None

    def __new__(
        cls,
        info: strawberry.Info,
        **kwargs,  # noqa: ARG003
    ) -> "AsyncDataLoader":
        """
        Returns a dataloader instance.
        Takes the instance from request context cache or create a new one if it does not exist there yet.
        This makes the dataloader "semi-singleton" in the sense that they are a singleton
        in the context of each request.
        """
        from strawberry_vercajk._base.extensions import dataloaders_context_var
        dataloaders = dataloaders_context_var.get()
        if cls not in dataloaders:
            dl = super().__new__(cls)
            dataloaders[cls] = dl
        return dataloaders[cls]

    def __init__(
        self,
        info: strawberry.Info,
    ) -> None:
        from strawberry_vercajk._base.extensions import dataloaders_context_var
        dataloaders = dataloaders_context_var.get()
        if self._instance_cache is None:
            self._instance_cache = dataloaders[type(self)]
            self.info = info
            super().__init__(load_fn=self._load_fn)

    @abc.abstractmethod
    async def _load_fn(
        self,
        keys: typing.Sequence[K],
        /,
    ) -> typing.Sequence[R | BaseException]:
        """
        Function to load the raw results.
        Results can then be further processed by overriding `process_results`.
        """
