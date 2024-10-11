import dataclasses
import typing

import strawberry

LIST_QUERY = """
query {
    %(query_name)s(%(params)s) {
        pagination {
            %(pagination)s
        }
        items {
            %(fields)s
        }
    }
}
"""


class ListSort(typing.TypedDict):
    field: str
    direction: typing.Literal["ASC", "DESC"]


class ListPage(typing.TypedDict):
    pageNumber: int
    pageSize: int


class ListPagination(typing.TypedDict, total=False):
    currentPage: int
    itemsCount: int
    totalItemsCount: int
    pageSize: int
    totalPagesCount: int
    hasPreviousPage: bool
    hasNextPage: bool


class ListQueryKwargs(typing.TypedDict):
    query_name: str
    fields: list[str] | str
    page: typing.NotRequired[ListPage | str]
    sort: typing.NotRequired[list[ListSort] | str]
    filters: typing.NotRequired[dict[str, typing.Any] | str]


def get_list_query(**kwargs: typing.Unpack[ListQueryKwargs]) -> str:
    kwargs.setdefault("page", "")
    kwargs.setdefault("sort", "")
    kwargs.setdefault("filters", "")
    if isinstance(kwargs["page"], dict):
        kwargs["page"] = str(kwargs["page"]).replace("'", "")
    if isinstance(kwargs["sort"], list):
        kwargs["sort"] = f"{{ordering: {str(kwargs["sort"]).replace("'", "")}}}"
    if isinstance(kwargs["filters"], dict):
        # string values need to be wrapped in double quotes
        filters_str = ", ".join(
            f"{key}: {f'"{value}"' if isinstance(value, str) else value}" for key, value in kwargs["filters"].items()
        )
        kwargs["filters"] = f"{{{filters_str}}}"
    if isinstance(kwargs["fields"], list):
        kwargs["fields"] = "\n".join(kwargs["fields"])
    return LIST_QUERY % {
        "query_name": kwargs["query_name"],
        "pagination": "\n".join(typing.get_type_hints(ListPagination).keys()),
        "fields": kwargs["fields"],
        "params": ", ".join(
            f"{key}: {value}" for key, value in kwargs.items() if key not in ["query_name", "fields"] and value
        ),
    }
