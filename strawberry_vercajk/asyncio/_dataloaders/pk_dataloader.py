__all__ = [
    "AsyncPKDataLoader",
]

import abc
import typing

from strawberry_vercajk.asyncio._dataloaders import core


class ResultType(typing.Protocol):
    pk: typing.Any


class AsyncPKDataLoader[K: typing.Hashable, R: ResultType](core.AsyncDataLoader[K, R]):  # TODO test
    """
    Base loader to load objects by their primary key.

    EXAMPLE - load Alliance of Account:
        1. DATALOADER DEFINITION
        class PKAllianceDataLoader(AsyncPKDataLoader):
            @typing.override
            @classmethod
            async def get_by_ids(cls, ids: list[int]) -> list[models.Alliance]:
                return await get_alliances_by_ids(ids)

        2. USAGE
        @strawberry.type(models.Account)
        class AccountType:
            ...

            @strawberry.field
            @staticmethod
            def alliance(
                root: strawberry.Parent["models.Account"],
                info: "Info",
            ) -> list["Alliance"]:
                return await PKAllianceDataLoader(info=info).load(root.alliance_id)

    """

    @abc.abstractmethod
    async def get_by_ids(
        self,
        ids: typing.Sequence[int],
        /,
    ) -> typing.Sequence[R | BaseException]: ...

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
        results = await self.get_by_ids(ids)
        key_to_res: dict[K, R] = {r.pk: r for r in results}
        # ensure results are ordered in the same way as input keys
        return [key_to_res.get(id_) for id_ in ids]
