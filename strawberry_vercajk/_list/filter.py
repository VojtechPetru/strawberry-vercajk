import abc
import dataclasses
import functools
import types
import typing
import typing_extensions

import django.core.exceptions
import django.db.models
import strawberry
from django.db.models import Q, QuerySet
from strawberry.types.field import StrawberryField

from strawberry_vercajk._base import utils as base_utils
from strawberry_vercajk._validation.validator import InputValidator

if typing.TYPE_CHECKING:
    import pydantic.fields

__all__ = [
    "Filter",
    "Filterset",
    "ListFilterset",
    "model_filter",
]

# Add more when needed. See django.db.models.lookups or django.db.models.<FieldClass>.get_lookups().
_DBLookupType = typing.Literal[
    "exact",
    "iexact",
    "contains",
    "icontains",
    "in",
    "gt",
    "gte",
    "lt",
    "lte",
    "startswith",
    "istartswith",
    "endswith",
    "iendswith",
    "range",
    "isnull",
    "regex",
    "iregex",
    "date",
    "year",
    "month",
    "day",
    "week_day",
    "iso_week_day",
    "week",
    "iso_year",
    "quarter",
    "overlap",
]
_DB_LOOKUPS: set[typing.LiteralString] = set(typing.get_args(_DBLookupType))

_FILTER_MODEL_ATTR_NAME: typing.LiteralString = "__VERCAJK_MODEL"
_FILTERS_FILTERSET_ATTR_NAME: typing.LiteralString = "__VERCAJK_FILTERS"


@typing_extensions.dataclass_transform(
    order_default=True,
    field_specifiers=(
        StrawberryField,
        strawberry.field,
    ),
)
def model_filter[T: "Filterset"](
    model: type[django.db.models.Model],
) -> typing.Callable[[type[T]], type[T]]:
    @functools.wraps(model_filter)
    def wrapper(
        filterset_cls: type[T],
    ) -> type[T]:
        if hasattr(filterset_cls, _FILTER_MODEL_ATTR_NAME):
            # Seems like an edge case. Decide what to do if this happens, maybe namespace the attribute better.
            raise ValueError(f"`{_FILTER_MODEL_ATTR_NAME}` is already set for `{filterset_cls.__name__}`.")
        setattr(filterset_cls, _FILTER_MODEL_ATTR_NAME, model)
        filterset_cls._initialize_filters()  # noqa: SLF001
        return filterset_cls

    return wrapper


@dataclasses.dataclass
class FilterInterface:
    @abc.abstractmethod
    def get_filter_q(
        self,
        value: typing.Any,  # noqa: ANN401
        info: strawberry.Info,
    ) -> Q:
        """
        Get the filter expression for the filter.
        :param value: Value to filter by
        :param info: Info object
        :return: final filter expression
        """
        raise NotImplementedError

    @abc.abstractmethod
    def get_filters(self) -> list["Filter"]:
        """
        Get all filters of this filter.
        If the filter is a combination of multiple filters, it returns all of them.
        For example, if the filter is defined as `Filter1 & (Filter2() | Filter3())`,
        it returns [Filter1(), Filter2(), Filter3()].
        """
        raise NotImplementedError

    @abc.abstractmethod
    def annotate_qs(self, qs: QuerySet) -> QuerySet:
        """
        Annotate the queryset with the necessary annotations for the filter.
        :param qs: Queryset to annotate
        :return: Annotated queryset
        """
        raise NotImplementedError

    def __or__(self, other: "FilterInterface") -> typing.Self:
        """
        Return a new filter interface which is a combination of this and the other.
        This allows for the use of the | operator.

        Example:
        -------
            q: Annotated[
                str | None,
                base_inputs.list.Filter(model_field="first_name", lookup="icontains") |
                base_inputs.list.Filter(model_field="last_name", lookup="icontains"),
                pydantic.Field(
                    default=None,
                    description="Icontains search in first name or last name.",
                ),
            ]

        """

        @dataclasses.dataclass
        class OrFilter(FilterInterface):
            filter1: "FilterInterface"
            filter2: "FilterInterface"

            def get_filter_q(
                self,
                value: typing.Any,  # noqa: ANN401
                info: strawberry.Info,
            ) -> Q:
                return self.filter1.get_filter_q(value, info) | self.filter2.get_filter_q(value, info)

            def get_filters(self) -> list["Filter"]:
                return self.filter1.get_filters() + self.filter2.get_filters()

            def annotate_qs(self, qs: QuerySet) -> QuerySet:
                qs = self.filter1.annotate_qs(qs)
                return self.filter2.annotate_qs(qs)

        return OrFilter(self, other)

    def __and__(self, other: "FilterInterface") -> typing.Self:
        """
        Return a new filter interface which is a combination of this and the other.
        This allows for the use of the & operator.

        Example:
        -------
            both_first_and_last_name_icontains: Annotated[
                str | None,
                base_inputs.list.Filter(model_field="first_name", lookup="icontains") |
                base_inputs.list.Filter(model_field="last_name", lookup="icontains"),
                pydantic.Field(
                    default=None,
                    description="Both first and last name of user must contain given string.",
                ),
            ]

        """

        @dataclasses.dataclass
        class AndFilter(FilterInterface):
            filter1: "FilterInterface"
            filter2: "FilterInterface"

            def get_filter_q(
                self,
                value: typing.Any,  # noqa: ANN401
                info: strawberry.Info,
            ) -> Q:
                return self.filter1.get_filter_q(value, info) & self.filter2.get_filter_q(value, info)

            def get_filters(self) -> list["Filter"]:
                return self.filter1.get_filters() + self.filter2.get_filters()

            def annotate_qs(self, qs: QuerySet) -> QuerySet:
                qs = self.filter1.annotate_qs(qs)
                return self.filter2.annotate_qs(qs)

        return AndFilter(self, other)

    def __invert__(self) -> typing.Self:
        """
        Return a new filter interface which is a negation of the original.
        This allows for the use of the ~ operator.

        Example:
        -------
            is_active: Annotated[
                bool | None,
                ~base_inputs.list.Filter(model_field="is_blacklisted", lookup="exact"),
                pydantic.Field(
                    default=None,
                    description="Filter by whether the object is active (i.e., is not blacklisted).",
                )
            ]

        """

        @dataclasses.dataclass
        class NegationFilter(FilterInterface):
            filter: "FilterInterface"

            def get_filter_q(
                self,
                value: typing.Any,  # noqa: ANN401
                info: strawberry.Info,
            ) -> Q:
                return ~self.filter.get_filter_q(value, info)

            def get_filters(self) -> list["Filter"]:
                return self.filter.get_filters()

            def annotate_qs(self, qs: QuerySet) -> QuerySet:
                return self.filter.annotate_qs(qs)

        return NegationFilter(self)


class Filter(FilterInterface):
    """
    Filter for an input field inside a Filterset.
    It should be used as an annotation on the field.
    For example:
        @model_filter(models.User)
        class UserFilterset(Filterset):
            q: typing.Annotated[
                str | None,
                Filter(model_field="first_name", lookup="icontains") |   <--- here
                Filter(model_field="last_name", lookup="icontains"),      <--- and here
                pydantic.Field(
                    default=None,
                    description="Icontains search in first name or last name.",
                )
            ]
            ... other filters
    """

    def __init__[QsT: "QuerySet"](
        self,
        model_field: typing.LiteralString | None = None,
        lookup: _DBLookupType | None = None,
        qs_annotation: typing.Callable[[QsT], QsT] | None = None,
        *,
        is_annotated: bool | None = None,
        prepare_value: typing.Callable[[typing.Any], typing.Any] | None = None,
    ) -> None:
        """
        :param model_field: Name of the model field to filter by. If not specified, it will be inferred from the name.
        :param lookup: Lookup to use for the filter. If not specified, it will be inferred from the field type or name.
        :param qs_annotation: Queryset annotation method needed for the filter.
            Example: Filter(..., qs_annotation=models.ProtectiveGearQuerySet.with_stocked_amount_status)
        :param is_annotated: Whether the field is annotated. If not specified, it will be inferred from 'qs_annotation'.
        :param prepare_value: Function to prepare the value received from FE before passing it to the filter.
        """
        self._model_field = model_field
        self._lookup = lookup
        self.qs_annotation = qs_annotation
        if is_annotated is None and qs_annotation is not None:
            is_annotated = True
        self.is_annotated: bool = False if is_annotated is None else is_annotated
        self._prepare_value = prepare_value

        # assigned by the filter
        self.__field_name: typing.LiteralString | None = None
        self.__field_type: type | None = None
        self.__filterset_cls: type[Filterset] | None = None

    def __str__(self) -> str:
        return (
            f"({type(self).__name__}) "
            f"{self.__filterset_cls.__name__ if self.__filterset_cls else ""}."
            f"{self.__field_name if self.__field_name else ""}"
        )

    @property
    def field_name(self) -> typing.LiteralString:
        """Name of the field on the filterset"""
        if self.__field_name is None:
            raise ImproperlyInitializedFilterError(self)
        return self.__field_name

    @property
    def filterset_cls(self) -> type["Filterset"]:
        if self.__filterset_cls is None:
            raise ImproperlyInitializedFilterError(self)
        return self.__filterset_cls

    @functools.cached_property
    def is_list(self) -> bool:
        if self.filterset_field_type is list:
            # e.g., when the field is annotated as a list | None
            # Should not happen, because we're already checking for this in FilterSet._check_field_type
            return True
        if typing.get_origin(self.filterset_field_type) is list:
            # e.g., when the field is annotated as list[str]
            return True
        inner_types: tuple[type, ...] = typing.get_args(self.filterset_field_type)
        if not inner_types:
            # e.g., when the field is annotated just as str
            return False
        # If there are inner types, it must be a union with None (i.e., is Optional).
        # This is also checked in FilterSet._check_field_type
        non_null_types: list[type] = [t for t in inner_types if t is not type(None)]
        if len(non_null_types) == 0:
            # I'm not really sure if this can happen, because None | None annotation is not allowed, but just in case
            raise FilterFieldTypeNotSupportedError(
                f"`{self.filterset_cls.__name__}.{self.field_name}` filter "
                f"does not support union types other than`<type> | None`, i.e., optional field..",
            )
        if len(non_null_types) > 1:
            # e.g., when the field is annotated as str | int | None
            raise FilterFieldTypeNotSupportedError(
                f"`{self.filterset_cls.__name__}.{self.field_name}` filter "
                f"does not support union types other than `<type> | None`, i.e., optional field..",
            )
        non_null_type: type = non_null_types[0]
        if non_null_type is list:
            raise FilterFieldTypeNotSupportedError(
                f"`{self}` filter annotated as `{self.filterset_field_type}` is not supported. You must specify "
                f"the type of the list, for example `list[str]`.",
            )
            # e.g., when the field is annotated as list | None
        return typing.get_origin(non_null_type) is list  # True when the field is annotated as list[str] | None

    @functools.cached_property
    def lookup(self) -> _DBLookupType:
        """
        Get the lookup to use for the filter. If not specified, it will be inferred from the field type of name.
        :return: Expression to use for the filter.
        """
        if self._lookup:
            return self._lookup

        suffix_inferred_lookup: str | None = self.field_name.split("_")[-1]
        if suffix_inferred_lookup not in _DB_LOOKUPS:
            suffix_inferred_lookup = None
        if self.is_list:
            if suffix_inferred_lookup and suffix_inferred_lookup not in ["in", "overlap"]:
                raise FilterFieldLookupAmbiguousError(
                    f"\n{self.filterset_cls.__name__}.{self.field_name} filter `{type(self).__name__}` has\n"
                    f"an inferred lookup `{suffix_inferred_lookup}` which does not support list as input,\n"
                    f"yet the field is annotated as `{self.filterset_field_type}`.",
                )
            return "in"
        return typing.cast(_DBLookupType, suffix_inferred_lookup or "exact")

    @property
    def model_field(self) -> typing.LiteralString:
        """Field name on the Django database model"""
        if self._model_field:
            return self._model_field
        return typing.cast(typing.LiteralString, self.field_name.removesuffix(f"_{self.lookup}"))

    def get_filter_q(
        self,
        value: typing.Any,  # noqa: ANN401
        info: strawberry.Info,  # noqa: ARG002
    ) -> Q:
        """Get the filter expression for the filter."""
        cleaned_value = self.prepare_value(value)
        return Q(**{f"{self.model_field}__{self.lookup}": cleaned_value})

    def get_filters(self) -> list[typing.Self]:
        return [self]

    def annotate_qs(self, qs: QuerySet) -> QuerySet:
        if not self.qs_annotation:
            return qs
        return self.qs_annotation(qs)

    def prepare_value(self, value: typing.Any) -> typing.Any:  # noqa: ANN401
        if self._prepare_value is None:
            return value
        return self._prepare_value(value)

    @property
    def filterset_field(self) -> "pydantic.fields.FieldInfo":
        return self.filterset_cls.model_fields[self.field_name]

    @property
    def filterset_field_type(self) -> type:
        return self.filterset_field.annotation

    @field_name.setter
    def field_name(self, value: typing.LiteralString) -> None:
        self.__field_name = value

    @filterset_cls.setter
    def filterset_cls(self, value: type["Filterset"]) -> None:
        self.__filterset_cls = value


class ListFilterset:
    @abc.abstractmethod
    def filter[T](self, data: list[T]) -> list[T]:
        raise NotImplementedError


class Filterset(InputValidator):
    """
    Filterset for filtering a list of objects.
    It should be used together with the `model_filter` decorator.
    For example:

        @model_filter(models.User)
        class UserFilterset(Filterset):
            q: typing.Annotated[
                str | None,
                Filter(model_field="first_name", lookup="icontains") |
                Filter(model_field="last_name", lookup="icontains"),
                pydantic.Field(
                    default=None,
                    description="Icontains search in first name or last name.",
                )
            ]
            ... other filters ...
    """

    def filter[T](self, qs: django.db.models.QuerySet[T], info: strawberry.Info) -> django.db.models.QuerySet[T]:
        """Perform the filtering on the queryset."""
        filters = self.get_filters()
        for field_name, field_filter in filters.items():
            field_filter: FilterInterface
            input_value = getattr(self, field_name)
            # Ideally, we'd like to check for strawberry.UNSET instead of None.
            # But it doesn't work for some reason and None is always passed.
            # We may need to handle this some way in the future...
            if input_value is None:
                continue
            qs = field_filter.annotate_qs(qs)
            qs = qs.filter(field_filter.get_filter_q(input_value, info))
        return qs

    @classmethod
    def get_filters(cls) -> dict[typing.LiteralString, FilterInterface]:
        """
        Get all filters of this filterset.
        :return: Dict of filters, where key is the field name and value are filters.
        """
        if not hasattr(cls, _FILTERS_FILTERSET_ATTR_NAME):
            raise ImproperlyInitializedFilterSetError(cls)
        return getattr(cls, _FILTERS_FILTERSET_ATTR_NAME)

    @classmethod
    def get_django_model(cls) -> type[django.db.models.Model]:
        """Django database model for this filterset. It is set by the `model_filter` decorator."""
        if not hasattr(cls, _FILTER_MODEL_ATTR_NAME):
            raise ImproperlyInitializedFilterSetError(cls)
        return getattr(cls, _FILTER_MODEL_ATTR_NAME)

    @classmethod
    def _initialize_filters(cls) -> None:
        """
        Initiate and check the filters for this filterset.
        It assigns the necessary attributes to the Filter annotations,
        checks if the filters are properly annotated, whether the model fields exist, and so on.
        This method is called automatically by the `model_filter` decorator and should not be called manually.
        """
        ret: dict[str, FilterInterface] = {}
        for field_name, field in cls.model_fields.items():
            cls._check_field_type(field.annotation)
            field_filters: list[FilterInterface] = []
            for annotation in field.metadata:
                if not cls._is_filter_annotation(annotation):
                    continue
                annotation: FilterInterface
                for filter_ in annotation.get_filters():
                    filter_.filterset_cls = cls
                    filter_.field_name = field_name
                    cls._check_lookup_is_resolvable(filter_)
                    cls._check_field_exists(filter_)
                field_filters.append(annotation)

            if not field_filters:
                raise MissingFilterAnnotationError(
                    f"\nField `{cls.__name__}.{field_name}` must be annotated with at exactly one filter. "
                    f"Example: `{cls.__name__}.{field_name}: typing.Annotated[str, Filter()] = ...`",
                )
            if len(field_filters) > 1:
                raise MoreThanOneFilterAnnotationError(
                    f"\nField `{cls.__name__}.{field_name}` must be annotated with exactly one filter.\n"
                    f"Instead, it is annotated with {len(field_filters)} filters.\n"
                    f"If you want to filter by multiple fields, you can combine filters using `|` (or), `&` (and), "
                    f"`~` (not) operators.",
                )
            ret[field_name] = field_filters[0]
        setattr(cls, _FILTERS_FILTERSET_ATTR_NAME, ret)

    @classmethod
    def _is_filter_annotation(cls, annotation: object | type) -> bool:
        """Checks if some the annotation is a Filter annotation (and not for instance pydantic validator)."""
        # The Filter should always be an instance, not a class (i.e., it should be used as `Filter()`, not `Filter`).
        try:
            not_an_instance: bool = issubclass(annotation, FilterInterface)
        except TypeError:
            not_an_instance = False
        if not_an_instance:
            raise FilterFieldNotAnInstanceError(
                f"`{Filter.__name__}` on `{cls.__name__}` must be used as an instance. "
                f"Please use `{annotation.__name__}()` instead.",
            )

        # Can be some other annotation. For example, pydantic validators.
        return isinstance(annotation, FilterInterface)

    @classmethod
    def _check_lookup_is_resolvable(cls, f: "Filter") -> None:
        """Checks if the lookup is resolvable for the field type."""
        if f.is_list and f.lookup not in ["in", "overlap"]:
            raise FilterFieldLookupAmbiguousError(
                f"`{cls.__name__}.{f.field_name}` filter `{type(f).__name__}` has "
                f"a lookup `{f.lookup}` which does not support list as input, yet "
                f"the field is annotated as `{f.filterset_field_type}`.",
            )

    @classmethod
    def _check_field_exists(cls, f: "Filter") -> None:
        """Checks if the field exists on the model."""
        if f.is_annotated:
            # The field is annotated -> not a model field -> no need to check if it exists on the model
            return
        base_utils.check_django_field_exists(cls.get_django_model(), f.model_field)

    @classmethod
    def _check_field_type(cls, field_annotation: type) -> None:
        if field_annotation is type(None):
            # case when the field is annotated as None
            raise FilterFieldTypeNotSupportedError(
                f"`{cls.__name__}` filter annotated as `{field_annotation}` is not supported.",
            )
        if field_annotation is list:
            # case when the field is annotated as a list
            raise FilterFieldTypeNotSupportedError(
                f"`{cls.__name__}` filter annotated as `{field_annotation}` is not supported. You must specify "
                f"the type of the list, for example `list[str]`.",
            )
        field_origin_type = typing.get_origin(field_annotation)  # for example, list[str] -> list; str -> None
        if all(ft is not types.UnionType for ft in [field_annotation, field_origin_type]):
            return

        # If the field type is a union, it must be a union with None (i.e., is Optional).
        # Otherwise, we don't support such a field (at least not at the moment).
        field_union_types = typing.get_args(field_annotation)
        allowed_number_of_union_types: int = 2
        if len(field_union_types) != allowed_number_of_union_types or type(None) not in field_union_types:
            raise FilterFieldTypeNotSupportedError(
                f"`{cls.__name__}` filter annotated as `{field_annotation}` is not supported. "
                f"We do not support complex union types other than `<type> | None`, i.e., optional field.",
            )


# Exceptions
class FilterFieldTypeNotSupportedError(Exception):
    pass


class FilterFieldModelFieldMismatchError(Exception):
    pass


class FilterFieldLookupAmbiguousError(Exception):
    pass


class FilterFieldNotAnInstanceError(Exception):
    pass


@dataclasses.dataclass
class ImproperlyInitializedFilterSetError(Exception):
    filter_set_cls: type[Filterset]

    def __str__(self) -> str:
        return (
            f"`{self.filter_set_cls.__name__}` is not properly initialized. "
            f"Did you forget to use `@{model_filter.__name__}` decorator on it?"
        )


@dataclasses.dataclass
class ImproperlyInitializedFilterError(Exception):
    filter: Filter

    def __str__(self) -> str:
        return (
            f"`{self.filter}` is not properly initialized. "
            f"Did you forget to use `@{model_filter.__name__}` decorator on its FilterSet?"
        )


class MissingFilterAnnotationError(Exception):
    pass


class MoreThanOneFilterAnnotationError(Exception):
    pass
