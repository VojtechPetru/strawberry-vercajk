import dataclasses
import types
import typing

import pydantic
import pydantic_core
import pydbull
import strawberry
from strawberry.experimental.pydantic.conversion import convert_strawberry_class_to_pydantic_model

from strawberry_vercajk._validation import constants, directives
from strawberry_vercajk._validation.validator import ValidatedInput

__all__ = [
    "InputFactory",
]

# GraphQL doesn't support working with larger integers than this.
# We could define custom scalar, but for now it's not necessary.
# See https://github.com/graphql/graphql-spec/issues/73.
DIRECTIVE_MAX: int = 2_147_483_647
DIRECTIVE_MIN: int = -DIRECTIVE_MAX


def _none_to_empty_string(value: typing.Any) -> typing.Any:  # noqa: ANN401
    return "" if value is None else value


_PYDANTIC_TYPE_MAP = {
    pydantic.EmailStr: str,
    pydantic.SecretStr: str,
    pydantic.SecretBytes: bytes,
    pydantic.AnyUrl: str,
    pydantic_core.MultiHostUrl: str,
}


class InputFactory:
    """
    Factory for creating GraphQL input type from InputValidator type
    """

    _REGISTRY: typing.ClassVar[dict[type["pydantic.BaseModel"], type["ValidatedInput"]]] = {}

    @classmethod
    def make[T: pydantic.BaseModel](
        cls,
        input_validator: type[T],
        *,
        name: typing.LiteralString | None = None,
    ) -> type[ValidatedInput[T]]:
        """
        Take a pydantic models and return a `ValidatedInput` GraphQL type.
        Take all fields from the validator and create a strawberry input with all fields annotated by `strawberry.auto`.
        :param input_validator: pydantic.BaseModel subclass
        :param name: Name of the returned GraphQL type
        """
        if input_validator in cls._REGISTRY:
            return cls._REGISTRY[input_validator]

        if name is None:
            name = typing.cast(typing.LiteralString, input_validator.__name__.removesuffix("Validator"))

        fields = input_validator.model_fields.copy()
        for field_info in fields.values():
            # If the field is also a pydantic model, we need to create a GraphQL input for it as well.
            if nested_input_validator := cls.__get_input_validator(field_info.annotation):
                cls.make(nested_input_validator)

        input_fields: list[tuple[str, type, strawberry.field]] = []
        field_convertors_any: bool = False
        for field_name, field_info in fields.items():
            field_constraints_directive = cls.extract_constrains(input_validator, field_info)
            field_type, field_convertors = cls._get_field_annotation(field_info)
            field_convertors_any = field_convertors_any or field_convertors
            input_validator.model_fields[field_name].metadata.extend(field_convertors)
            if field_constraints_directive:
                strawberry_field = strawberry.field(
                    directives=[
                        field_constraints_directive,
                    ],
                    deprecation_reason=field_info.deprecated,
                )
            else:
                strawberry_field = strawberry.field(
                    deprecation_reason=field_info.deprecated,
                )
            input_fields.append((field_name, field_type, strawberry_field))
        if field_convertors_any:
            # If any field has a new convertor, we need to rebuild the model.
            input_validator.model_rebuild(force=True)
        input_cls = type(
            name,
            (ValidatedInput,),
            {name: value for name, annot, value in input_fields},
        )
        input_cls.__annotations__ = {name: annot for name, annot, value in input_fields}

        gql_input = typing.cast(
            type[ValidatedInput[T]],
            strawberry.experimental.pydantic.input(input_validator, name=name)(input_cls),
        )
        gql_input.to_pydantic = cls.to_pydantic
        setattr(gql_input, constants.INPUT_VALIDATOR_ATTR_NAME, input_validator)
        cls._REGISTRY[input_validator] = gql_input
        return gql_input

    @classmethod
    def _get_field_annotation(
        cls,
        field_info: "pydantic.fields.FieldInfo",
    ) -> tuple[type, list[pydantic.BeforeValidator | pydantic.AfterValidator]]:
        """
        Get the annotation for a strawberry field.
        If the new annotation requires a before/after validation convertor, it is returned as well.
        """
        if field_info.annotation is str and not field_info.is_required():
            # Mark string fields which have a default value as not required.
            return typing.Optional[field_info.annotation], [pydantic.BeforeValidator(_none_to_empty_string)]  # noqa: UP007

        if typing.get_origin(field_info.annotation) is not typing.Union:
            return strawberry.auto, []
        ret_types: list[type] = []
        convertors: list[pydantic.BeforeValidator | pydantic.AfterValidator] = []
        is_auto: bool = True  # whether "strawberry.auto" should be used
        for internal_type in typing.get_args(field_info.annotation):
            internal_origin_type = cls._get_origin_type_from_annotated_type(internal_type)
            if internal_origin_type is typing.Literal[""]:
                # Replace typing.Literal[""] with NoneType
                #  - let the field appear as optional in the gql schema
                #  - convert None back to empty string when data is received
                is_auto = False
                ret_types.append(types.NoneType)
                convertors.append(pydantic.BeforeValidator(_none_to_empty_string))
            else:
                ret_types.append(
                    _PYDANTIC_TYPE_MAP.get(internal_origin_type, internal_type),
                )

        if is_auto:
            return strawberry.auto, []
        return typing.Union[*ret_types], convertors

    @classmethod
    def __get_input_validator(cls, annotation: type) -> type[pydantic.BaseModel] | None:
        try:
            return cls.__get_from_complex_type(annotation, pydantic.BaseModel)
        except TypeError:
            return None

    @classmethod
    def __get_from_complex_type[T](cls, from_type: type, type_: type[T]) -> type[T]:
        """
        Get the type from a complex type.
        For example, if `t` is `enum.Enum`, this method will return SomeEnum for 'from_type' of types
         - `SomeEnum`
         - `SomeEnum | None`
         - `Optional[SomeEnum]`
         - `list[SomeEnum]`
         - `list[SomeEnum | None]`
        :param from_type: The type to get the type from
        :param type_: The type to get
        :raises TypeError: if the type is not found
        """
        if typing.get_origin(from_type) in [types.UnionType, typing.Union]:
            for internal_type in typing.get_args(from_type):
                try:
                    return cls.__get_from_complex_type(internal_type, type_)
                except TypeError:
                    pass
        if typing.get_origin(from_type) is list:
            for args in typing.get_args(from_type):
                try:
                    return cls.__get_from_complex_type(args, type_)
                except TypeError:
                    pass
        if issubclass(from_type, type_):  # may raise TypeError
            return from_type
        raise TypeError

    @classmethod
    def _get_origin_type_from_annotated_type(cls, t: type) -> type:
        """
        Get the origin type from an annotated type.
        For example, if `t` is `Annotated[str, ...]`, this method will return `str`.
        :param t: The type to get the origin type from
        """
        if typing.get_origin(t) is typing.Annotated:
            return cls._get_origin_type_from_annotated_type(typing.get_args(t)[0])
        return t

    @classmethod
    def extract_constrains(
        cls,
        input_validator: pydantic.BaseModel,
        field_info: "pydantic.fields.FieldInfo",
    ) -> directives.FieldConstraintsDirective:
        def clean_value(value: typing.Any) -> typing.Any:  # noqa: ANN401
            if value is pydantic_core.PydanticUndefined:
                return None
            if isinstance(value, int):
                return min(max(DIRECTIVE_MIN, value), DIRECTIVE_MAX)
            return value if value is not pydantic_core.PydanticUndefined else None

        pydantic_adapter = pydbull.PydanticAdapter(type(input_validator))
        return directives.FieldConstraintsDirective(
            gt=clean_value(pydantic_adapter.get_greater_than(field_info)),
            gte=clean_value(pydantic_adapter.get_greater_than_or_equal(field_info)),
            lt=clean_value(pydantic_adapter.get_less_than(field_info)),
            lte=clean_value(pydantic_adapter.get_less_than_or_equal(field_info)),
            min_length=clean_value(pydantic_adapter.get_min_length(field_info)),
            max_length=clean_value(pydantic_adapter.get_max_length(field_info)),
            max_digits=clean_value(pydantic_adapter.get_decimal_max_digits(field_info)),
            decimal_places=clean_value(pydantic_adapter.get_decimal_places(field_info)),
            pattern=clean_value(pydantic_adapter.get_pattern(field_info)),
            multiple_of=clean_value(pydantic_adapter.get_multiple_of(field_info)),
        )

    @staticmethod
    def to_pydantic(
        self: "ValidatedInput",  # noqa: PLW0211
        is_inner: bool = True,
        **kwargs,
    ) -> dict | pydantic.BaseModel:
        """
        Overrides the default strawberry `to_pydantic` method (see `to_pydantic_default` in strawberry).
        The reason for this is that we need to validate the whole pydantic object at once.
        The default strawberry method converts the input data to a pydantic model field by field (if nested).
        This raises the pydantic validation error on the first error, and therefore fails with a single exception
        on the first nested pydantic object which is invalid and doesn't validate further.
        For this reason, we don't convert the nested pydantic objects to pydantic models but keep them as
        dictionaries and then insert this dictionary into the parent (outermost) pydantic object.
        This way, pydantic validates the whole object at once, and we get all validation errors.
        """
        instance_kwargs = {
            f.name: convert_strawberry_class_to_pydantic_model(
                getattr(self, f.name),
            )
            for f in dataclasses.fields(self)
        }
        instance_kwargs.update(kwargs)
        if not is_inner:
            return self.get_validator()(**instance_kwargs)
        return instance_kwargs
