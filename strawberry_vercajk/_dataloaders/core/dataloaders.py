__all__ = ("BaseDataLoader",)

import abc
import typing

import graphql_sync_dataloaders
import strawberry

_DATALOADERS_ATTR = "_vercajk_dataloaders"


class BaseDataLoader[K: typing.Hashable, R](graphql_sync_dataloaders.SyncDataLoader):
    _batch_load_fn: typing.Callable[[list[K]], list[R]]
    _cache: dict[K, "graphql_sync_dataloaders.SyncFuture[R]"]
    _queue: list[tuple[K, "graphql_sync_dataloaders.SyncFuture[R]"]]

    # serves two purposes:
    # 1. "mark" that the class instance was already created
    # 2. don't allow creating more than one instance of the class (see __init__)
    _instance_cache: type[typing.Self] | None = None

    def __new__(
        cls,
        info: strawberry.Info,  # noqa: ARG004
        **kwargs,  # noqa: ARG004
    ) -> "BaseDataLoader":
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
            super().__init__(batch_load_fn=self._processed_load_fn)

    @property
    @abc.abstractmethod
    def load_fn(self) -> typing.Callable[[list[K]], list[R] | typing.Mapping[K, R]]:
        """
        Function to load the raw results.
        Results can then be further processed by overriding `process_results`.
        """
        raise NotImplementedError

    def process_results(self, keys: list[K], results: list[R] | typing.Mapping[K, R]) -> list[R]:  # noqa: ARG002
        """
        Hook for subclasses to implement custom processing of the results.
        """
        return results

    def _processed_load_fn(self, keys: list[K]) -> list[R]:
        results = self.load_fn(keys)
        return self.process_results(keys, results)

    def prime(self, key: K, value: R, force: bool = False) -> None:
        self.prime_many({key: value}, force)

    def prime_many(self, data: typing.Mapping[K, R], force: bool = False) -> None:
        # Populate the cache with the specified values
        for key, value in data.items():
            if not self._cache.get(key) or force:
                future = graphql_sync_dataloaders.SyncFuture()
                future.set_result(value)
                self._cache[key] = future

        # If there are any pending tasks in the queue with provided key, resolve them
        if self._queue is not None:
            for task_key, task_future in self._queue:
                if task_key in data:
                    task_future.set_result(data[task_key])
