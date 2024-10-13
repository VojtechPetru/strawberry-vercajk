import dataclasses
import time
import typing
from collections import defaultdict

import django.db


@dataclasses.dataclass
class _DbQuery:
    """Log of a single database query."""

    sql: str
    params: tuple
    many: bool
    duration: float | None = None
    exception: Exception | None = None


@dataclasses.dataclass
class _DbQueryGroup:
    """Log of a group of database queries."""

    queries: list["_DbQuery"] = dataclasses.field(default_factory=list)

    def __str__(self) -> str:
        return f"{self.num_queries} queries in {self.total_duration:.3f}s"

    @property
    def total_duration(self) -> float:
        """Total duration of all queries in seconds."""
        return sum(q.duration for q in self.queries if q.duration is not None)

    @property
    def num_queries(self) -> int:
        """Number of queries."""
        return len(self.queries)

    @property
    def duplicates(self) -> list["_DbQueryGroup"]:
        """Queries that are duplicated."""
        sql_to_queries: dict[str, list[_DbQuery]] = defaultdict(list)
        for query in self.queries:
            sql_to_queries[query.sql].append(query)
        return [_DbQueryGroup(queries=queries) for queries in sql_to_queries.values() if len(queries) > 1]


@dataclasses.dataclass
class QueryLogger(_DbQueryGroup):
    """
    A wrapper for django.db.connection.execute_wrapper that logs the database queries.
    This can be used as an instrumentation tool for performance testing during development.

    Example usage:
        with QueryLogger() as ql:
            # do some stuff including db queries
        print(ql.queries)
    """

    def __enter__(self):
        for connection in django.db.connections.all():
            connection.execute_wrappers.append(self)
        return self

    def __exit__(self, *args, **kwargs) -> None:
        for connection in django.db.connections.all():
            try:
                connection.execute_wrappers.remove(self)
            except ValueError:
                pass

    def __call__(
        self,
        execute: typing.Callable,
        sql: str,
        params: tuple,
        many: bool,
        context: dict[str, typing.Any],
    ) -> None:
        current_query = _DbQuery(
            sql=sql,
            params=params,
            many=many,
        )
        start = time.monotonic()
        try:
            result = execute(sql, params, many, context)
        except Exception as e:
            current_query.exception = e
            raise
        else:
            return result
        finally:
            duration = time.monotonic() - start
            current_query.duration = duration
            self.queries.append(current_query)
