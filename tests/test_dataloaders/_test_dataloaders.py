import timeit
import typing

import graphql_sync_dataloaders
import pytest
import strawberry
import strawberry_vercajk
from strawberry_vercajk._dataloaders import PKDataLoaderFactory
from strawberry_vercajk._dataloaders.core import InfoDataloadersContextMixin

from tests.app import models, factories
from tests.app.graphql import types
from tests.app.graphql.dataloader_types import auto_dataloader_types, dataloader_factory_types, dataloader_types
from tests.app.graphql.dataloader_types.dataloader_types import FruitDataLoader

if typing.TYPE_CHECKING:
    from strawberry.types import ExecutionResult

_FRUIT_COUNT: int = 5

# query for user direct permissions, query for user role permissions
# 1 for root, 4 x <num_fruits> for nested + <varieties> x <fruits> for varieties -> fruits M2M
_NO_DATALOADERS_QUERY_COUNT: int = 186
_DATALOADERS_QUERY_COUNT: int = (
        # root
        1 +
        # each nested "simple" (and reverse OneToOne) dataloader
        4 * 1 +
        # each M2M: root (fruit) -> varieties; varieties -> fruits
        1 * 2
)


def assert_lists_equal(*lists: list):
    for i, l in enumerate(lists):
        if i == 0:
            continue
        assert l == lists[0]


@strawberry.type
class Query:
    @strawberry.field()
    def fruits(self) -> list[types.FruitType]:
        return models.Fruit.objects.all()

    @strawberry.field()
    def fruits_with_dataloaders(self, info: strawberry.Info) -> list[dataloader_types.FruitTypeDataLoaders]:
        fruits = models.Fruit.objects.all()
        FruitDataLoader(info).prime_many({f.pk: f for f in fruits})
        return fruits

    @strawberry.field()
    def fruits_with_dataloader_factories(self, info: strawberry.Info) -> list[dataloader_factory_types.FruitTypeDataLoaderFactories]:
        fruits = models.Fruit.objects.all()
        loader = PKDataLoaderFactory.make(config={"model": models.Fruit})
        loader(info).prime_many({f.pk: f for f in fruits})
        return fruits

    @strawberry.field()
    def fruits_with_auto_dataloader_fields(self, info: strawberry.Info) -> list[auto_dataloader_types.FruitAutoDataLoaderType]:
        fruits = models.Fruit.objects.all()
        loader = PKDataLoaderFactory.make(config={"model": models.Fruit})
        loader(info).prime_many({f.pk: f for f in fruits})
        return fruits


test_schema = strawberry.Schema(
    query=Query,
    mutation=None,
    execution_context_class=graphql_sync_dataloaders.DeferredExecutionContext,
)


QUERY_TPL = """
    %s {
        id
        name
        color {
            id
            name
        }
        plant {
            id
            name
            fruit {  # tests the reverse OneToOne dataloader
                id
                name
            }
        }
        varieties {
            id
            name
            fruits {  # tests the M2M dataloader from the "other" side (the model that doesn't have the M2M field)
                id
                name
            }
        }
        eaters {
            id
            name
            favouriteFruit {  # <-- INTENTIONALLY REPEATED (SAME TYPE AS ROOT), SO DATALOADER CACHE IS TESTED
                id
                name
                color {
                    id
                    name
                }
                plant {
                    id
                    name
                    fruit {
                        id
                        name
                    }
                }
                varieties {
                    id
                    name
                    fruits {
                        id
                        name
                    }
                }
                eaters {
                    id
                    name
                }
            }
        }
    }
"""


def get_query(
        t: typing.Literal["simple", "dataloaders", "factories", "auto_dataloader_field"],
        /,
):
    if t == "simple":
        q = QUERY_TPL % "fruits"
    elif t == "dataloaders":
        q = QUERY_TPL % "fruitsWithDataloaders"
    elif t == "factories":
        q = QUERY_TPL % "fruitsWithDataloaderFactories"
    elif t == "auto_dataloader_field":
        q = QUERY_TPL % "fruitsWithAutoDataloaderFields"
    else:
        raise ValueError(f"Invalid query type: {t}")
    return f"{{ {q} }}"

def run_query(
        query: str,
        context: InfoDataloadersContextMixin | None = None,
):
    if context is None:
        context = InfoDataloadersContextMixin()
    return test_schema.execute_sync(query, context_value=context)

def check_response_data(resp: "ExecutionResult", fruits: typing.Iterable[models.Fruit]) -> None:
    assert resp.errors is None
    assert resp.data is not None
    data: list[dict] = resp.data.popitem()[1]  # assumes that there's only one key

    for fruit, db_fruit in zip(sorted(data, key=lambda x: x["id"]), sorted(fruits, key=lambda x: x.id)):
        db_fruit: "models.Fruit"
        assert fruit["id"] == db_fruit.pk
        assert fruit["name"] == db_fruit.name
        assert fruit["color"]["id"] == db_fruit.color.pk
        assert fruit["color"]["name"] == db_fruit.color.name
        assert fruit["plant"] == {
            "id": db_fruit.plant.pk,
            "name": db_fruit.plant.name,
            "fruit": {
                "id": db_fruit.plant.fruit.pk,
                "name": db_fruit.plant.fruit.name,
            },
        }

        assert_lists_equal(
            fruit["varieties"],
            [
                {
                    "id": v.pk,
                    "name": v.name,
                    "fruits": [
                        {
                            "id": f.pk,
                            "name": f.name,
                        }
                        for f in v.fruits.all()
                    ],
                }
                for v in db_fruit.varieties.all()
            ],
        )
        assert_lists_equal(
            fruit["eaters"],
            [
                {
                    "id": e.pk,
                    "name": e.name,
                    "favouriteFruit": {
                        "id": e.favourite_fruit.pk,
                        "name": e.favourite_fruit.name,
                        "color": {
                            "id": e.favourite_fruit.color.pk,
                            "name": e.favourite_fruit.color.name,
                        },
                        "plant": {
                            "id": e.favourite_fruit.plant.pk,
                            "name": e.favourite_fruit.plant.name,
                            "fruit": {
                                "id": e.favourite_fruit.plant.fruit.pk,
                                "name": e.favourite_fruit.plant.fruit.name,
                            },
                        },
                        "varieties": [
                            {
                                "id": v.pk,
                                "name": v.name,
                                "fruits": [
                                    {
                                        "id": f.pk,
                                        "name": f.name,
                                    }
                                    for f in v.fruits.all()
                                ],
                            }
                            for v in e.favourite_fruit.varieties.all()
                        ],
                        "eaters": [
                            {
                                "id": ee.pk,
                                "name": ee.name,
                            }
                            for ee in e.favourite_fruit.eaters.all()
                        ],
                    },
                }
                for e in db_fruit.eaters.all()
            ],
        )


@pytest.mark.django_db()
def test_no_dataloaders() -> None:
    fruits = factories.FruitFactory.create_batch(_FRUIT_COUNT, with_eaters=True, with_varieties=True)
    with strawberry_vercajk.QueryLogger() as ql:
        resp = run_query(get_query("simple"))
    # just to be sure we're testing the right thing (i.e., that we're not using dataloaders)
    assert len(ql.duplicates) is not 0
    assert ql.num_queries == _NO_DATALOADERS_QUERY_COUNT
    check_response_data(resp, fruits)


@pytest.mark.django_db()
def test_dataloaders() -> None:
    fruits = factories.FruitFactory.create_batch(_FRUIT_COUNT, with_eaters=True, with_varieties=True)
    with strawberry_vercajk.QueryLogger() as ql:
        resp = run_query(get_query("dataloaders"))
    assert len(ql.duplicates) is 0
    assert ql.num_queries == _DATALOADERS_QUERY_COUNT
    check_response_data(resp, fruits)


@pytest.mark.django_db()
def test_dataloader_factories() -> None:
    fruits = factories.FruitFactory.create_batch(_FRUIT_COUNT, with_eaters=True, with_varieties=True)
    with strawberry_vercajk.QueryLogger() as ql:
        resp = run_query(get_query("factories"))
    assert len(ql.duplicates) is 0
    assert ql.num_queries == _DATALOADERS_QUERY_COUNT
    check_response_data(resp, fruits)


@pytest.mark.django_db()
def test_auto_dataloader_field() -> None:
    fruits = factories.FruitFactory.create_batch(_FRUIT_COUNT, with_eaters=True, with_varieties=True)
    with strawberry_vercajk.QueryLogger() as ql:
        resp = run_query(get_query("auto_dataloader_field"))
    assert len(ql.duplicates) is 0
    assert ql.num_queries == _DATALOADERS_QUERY_COUNT
    check_response_data(resp, fruits)


@pytest.mark.django_db()
def test_all_dataloader_approaches_make_the_same_db_queries() -> None:
    factories.FruitFactory.create_batch(_FRUIT_COUNT, with_eaters=True, with_varieties=True)
    with strawberry_vercajk.QueryLogger() as ql_dataloaders:
        run_query(get_query("dataloaders"))
    with strawberry_vercajk.QueryLogger() as ql_factories:
        run_query(get_query("factories"))
    with strawberry_vercajk.QueryLogger() as ql_auto_dataloader_field:
        run_query(get_query("auto_dataloader_field"))

    assert (
        [q.sql for q in ql_dataloaders.queries]
        == [q.sql for q in ql_factories.queries]
        == [q.sql for q in ql_auto_dataloader_field.queries]
    )
    assert (
        [q.params for q in ql_dataloaders.queries]
        == [q.params for q in ql_factories.queries]
        == [q.params for q in ql_auto_dataloader_field.queries]
    )
    assert (
        [q.many for q in ql_dataloaders.queries]
        == [q.many for q in ql_factories.queries]
        == [q.many for q in ql_auto_dataloader_field.queries]
    )
    assert (
        [q.exception for q in ql_dataloaders.queries]
        == [q.exception for q in ql_factories.queries]
        == [q.exception for q in ql_auto_dataloader_field.queries]
    )
    assert len(ql_dataloaders.queries) == _DATALOADERS_QUERY_COUNT


@pytest.mark.skip(reason="Dataloaders performance test to be run manually.")
@pytest.mark.django_db()
def test_performance_comparison() -> None:
    factories.FruitFactory.create_batch(100, with_eaters=True, with_varieties=True)

    no_dataloaders_time = timeit.timeit(lambda: run_query(get_query("simple")), number=10)
    dataloaders_time = timeit.timeit(lambda: run_query(get_query("dataloaders")), number=10)
    factories_time = timeit.timeit(lambda: run_query(get_query("factories")), number=10)
    auto_dataloader_field_time = timeit.timeit(lambda: run_query(get_query("auto_dataloader_field")), number=10)
    print(
        f"no_dataloaders: {no_dataloaders_time:.3f}s\n"
        f"dataloaders: {dataloaders_time:.3f}s\n"
        f"factories: {factories_time:.3f}s\n"
        f"auto_dataloader_field: {auto_dataloader_field_time:.3f}s"
    )
