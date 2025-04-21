__all__ = [
    "AsyncFKDataLoader",
]

import abc
import typing

import strawberry

from strawberry_vercajk.asyncio._dataloaders import core


class AsyncFKDataLoader[K: typing.Hashable, R](core.AsyncDataLoader[K, R]):  # TODO test
    """
    Base loader for reversed FK relationship (e.g., BlogPosts of a User).

    WARNING: This dataloader fetches *all* related objects for a given list of parent objects.
    If you need to, e.g., paginate, filter, or sort the related objects, use AsyncFKListDataLoader instead.
    """

    def __init__(
        self,
        info: strawberry.Info,
        *,
        one_to_one: bool = False,
    ) -> None:
        self.one_to_one = one_to_one
        super().__init__(info=info)

    @abc.abstractmethod
    async def get_items_map(
        self,
        ids: typing.Sequence[int],
        /,
    ) -> dict[K, list[R | BaseException]]: ...

    @typing.final
    @typing.override
    async def _load_fn(
        self,
        ids: typing.Sequence[int],
        /,
    ) -> typing.Sequence[R | BaseException]:
        """
        Function to load the raw results.
        Results can then be further processed by overriding `process_results`.
        """
        results = await self.get_items_map(ids)
        if self.one_to_one:
            return [results.get(key, [None])[0] for key in ids]
        return [results.get(key, []) for key in ids]
