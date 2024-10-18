import abc
import typing

import graphql_sync_dataloaders

from strawberry_vercajk._dataloaders.core import DataloadersContext


class BaseDataLoader[K, T](graphql_sync_dataloaders.SyncDataLoader):
    _batch_load_fn: typing.Callable[[list[K]], list[T]]
    _cache: dict[K, "graphql_sync_dataloaders.SyncFuture[T]"]
    _queue: list[tuple[K, "graphql_sync_dataloaders.SyncFuture[T]"]]

    # serves two purposes:
    # 1. "mark" that the class instance was already created
    # 2. don't allow creating more than one instance of the class (see __init__)
    _instance_cache: type[typing.Self] | None = None

    def __new__(cls, context: "DataloadersContext", *, force_new: bool = False) -> "BaseDataLoader":
        """
        Returns a dataloader instance.
        Takes the instance from request context cache or create a new one if it does not exist there yet.
        This makes the dataloader "semi-singleton" in the sense that they are a singleton
        in the context of each request.
        """
        if not isinstance(context, DataloadersContext):
            raise TypeError(
                # TODO write setup guide (custom Info class with overridden context property to `schema`)
                "strawberry.Info.context must be an instance of `strawberry_vercajk.DataloadersContext`.",
            )

        if force_new or cls not in context.dataloaders:
            context.dataloaders[cls] = super().__new__(cls)
        return context.dataloaders[cls]

    def __init__(self, context: "DataloadersContext") -> None:
        if self._instance_cache is None:
            self._instance_cache = context.dataloaders[type(self)]
            self.context = context
            super().__init__(batch_load_fn=self.load_fn)

    @abc.abstractmethod
    def load_fn(self, keys: list[K]) -> list[T]:
        """
        Get a list of keys and return a list of data-loaded values.
        Beware that the values must be in the same order as the keys!
        """
        raise NotImplementedError

    def prime(self, key: K, value: T, force: bool = False) -> None:
        self.prime_many({key: value}, force)

    def prime_many(self, data: typing.Mapping[K, T], force: bool = False) -> None:
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
