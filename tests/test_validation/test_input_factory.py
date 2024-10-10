import typing
from decimal import Decimal

import pydantic
from strawberry.schema_directive import StrawberrySchemaDirective, Location

from strawberry_vercajk import InputFactory, FieldConstraintsDirective


def test_input_factory_make_input() -> None:
    class Model(pydantic.BaseModel):
        name: typing.Annotated[str, pydantic.Field(description="Name of the model", deprecated="Deprecation reason")]

    gql_input = InputFactory.make(Model)
    definition = gql_input.__strawberry_definition__
    assert definition.name == "Model"
    assert len(definition.fields) == 1
    assert definition.fields[0].name == "name"
    assert definition.fields[0].description == "Name of the model"
    assert definition.fields[0].type_annotation.annotation is str
    assert definition.fields[0].deprecation_reason == "Deprecation reason"


def test_input_factory_make_is_cached() -> None:
    class Model(pydantic.BaseModel):
        name: str

    gql_input = InputFactory.make(Model)
    assert InputFactory._REGISTRY[Model] == gql_input
    gql_input_cached = InputFactory.make(Model)
    assert gql_input == gql_input_cached


def test_input_factory_make_with_nested_input() -> None:
    class NestedModel(pydantic.BaseModel):
        name: typing.Annotated[str, pydantic.Field(description="Name of the nested model")]

    class Model(pydantic.BaseModel):
        nested: typing.Annotated[NestedModel, pydantic.Field(description="Descr.", deprecated="Deprecation reason")]


    gql_input = InputFactory.make(Model)
    definition = gql_input.__strawberry_definition__
    assert definition.name == "Model"
    assert len(definition.fields) == 1
    assert definition.fields[0].name == "nested"
    assert definition.fields[0].type_annotation.annotation is InputFactory.make(NestedModel)
    assert definition.fields[0].description == "Descr."
    assert definition.fields[0].deprecation_reason == "Deprecation reason"
    assert definition.fields[0].type.__strawberry_definition__.name == "NestedModel"
    assert len(definition.fields[0].type.__strawberry_definition__.fields) == 1
    assert definition.fields[0].type.__strawberry_definition__.fields[0].name == "name"
    assert definition.fields[0].type.__strawberry_definition__.fields[0].type is str
    assert definition.fields[0].type.__strawberry_definition__.fields[0].description == "Name of the nested model"


def test_input_factory_make_with_nested_input_optional() -> None:
    class NestedModel(pydantic.BaseModel):
        name: typing.Annotated[str, pydantic.Field(description="Name of the nested model")]

    class Model(pydantic.BaseModel):
        nested: typing.Annotated[NestedModel | None, pydantic.Field(description="Descr.", deprecated="Deprecation reason")]


    gql_input = InputFactory.make(Model)
    definition = gql_input.__strawberry_definition__
    assert definition.name == "Model"
    assert len(definition.fields) == 1
    assert definition.fields[0].name == "nested"
    assert definition.fields[0].type_annotation.annotation == InputFactory.make(NestedModel) | None
    assert definition.fields[0].description == "Descr."
    assert definition.fields[0].deprecation_reason == "Deprecation reason"
    assert definition.fields[0].type.of_type.__strawberry_definition__.name == "NestedModel"
    assert len(definition.fields[0].type.of_type.__strawberry_definition__.fields) == 1
    assert definition.fields[0].type.of_type.__strawberry_definition__.fields[0].name == "name"
    assert definition.fields[0].type.of_type.__strawberry_definition__.fields[0].type is str
    assert definition.fields[0].type.of_type.__strawberry_definition__.fields[0].description == "Name of the nested model"


def test_input_factory_make_with_nested_input_list() -> None:
    class NestedModel(pydantic.BaseModel):
        name: typing.Annotated[str, pydantic.Field(description="Name of the nested model")]

    class Model(pydantic.BaseModel):
        nested: typing.Annotated[list[NestedModel], pydantic.Field(description="Descr.", deprecated="Deprecation reason")]


    gql_input = InputFactory.make(Model)
    definition = gql_input.__strawberry_definition__
    assert definition.name == "Model"
    assert len(definition.fields) == 1
    assert definition.fields[0].name == "nested"
    assert definition.fields[0].type_annotation.annotation == list[InputFactory.make(NestedModel)]
    assert definition.fields[0].description == "Descr."
    assert definition.fields[0].deprecation_reason == "Deprecation reason"
    assert definition.fields[0].type.of_type.__strawberry_definition__.name == "NestedModel"
    assert len(definition.fields[0].type.of_type.__strawberry_definition__.fields) == 1
    assert definition.fields[0].type.of_type.__strawberry_definition__.fields[0].name == "name"
    assert definition.fields[0].type.of_type.__strawberry_definition__.fields[0].type is str
    assert definition.fields[0].type.of_type.__strawberry_definition__.fields[0].description == "Name of the nested model"


def test_input_factory_make_with_nested_input_list_optional() -> None:
    class NestedModel(pydantic.BaseModel):
        name: typing.Annotated[str, pydantic.Field(description="Name of the nested model")]

    class Model(pydantic.BaseModel):
        nested: typing.Annotated[list[NestedModel] | None, pydantic.Field(description="Descr.", deprecated="Deprecation reason")]


    gql_input = InputFactory.make(Model)
    definition = gql_input.__strawberry_definition__
    assert definition.name == "Model"
    assert len(definition.fields) == 1
    assert definition.fields[0].name == "nested"
    assert definition.fields[0].type_annotation.annotation == list[InputFactory.make(NestedModel)] | None
    assert definition.fields[0].description == "Descr."
    assert definition.fields[0].deprecation_reason == "Deprecation reason"
    assert definition.fields[0].type.of_type.of_type.__strawberry_definition__.name == "NestedModel"
    assert len(definition.fields[0].type.of_type.of_type.__strawberry_definition__.fields) == 1
    assert definition.fields[0].type.of_type.of_type.__strawberry_definition__.fields[0].name == "name"
    assert definition.fields[0].type.of_type.of_type.__strawberry_definition__.fields[0].type is str
    assert definition.fields[0].type.of_type.of_type.__strawberry_definition__.fields[0].description == "Name of the nested model"


def test_input_factory_make_with_nested_input_list_optional_nested_optional() -> None:
    class NestedModel(pydantic.BaseModel):
        name: typing.Annotated[str, pydantic.Field(description="Name of the nested model")]

    class Model(pydantic.BaseModel):
        nested: typing.Annotated[list[NestedModel | None] | None, pydantic.Field(description="Descr.", deprecated="Deprecation reason")]

    gql_input = InputFactory.make(Model)
    definition = gql_input.__strawberry_definition__
    assert definition.name == "Model"
    assert len(definition.fields) == 1
    assert definition.fields[0].name == "nested"
    assert definition.fields[0].type_annotation.annotation == list[InputFactory.make(NestedModel) | None] | None
    assert definition.fields[0].description == "Descr."
    assert definition.fields[0].deprecation_reason == "Deprecation reason"
    assert definition.fields[0].type.of_type.of_type.of_type.__strawberry_definition__.name == "NestedModel"
    assert len(definition.fields[0].type.of_type.of_type.of_type.__strawberry_definition__.fields) == 1
    assert definition.fields[0].type.of_type.of_type.of_type.__strawberry_definition__.fields[0].name == "name"
    assert definition.fields[0].type.of_type.of_type.of_type.__strawberry_definition__.fields[0].type is str
    assert definition.fields[0].type.of_type.of_type.of_type.__strawberry_definition__.fields[0].description == "Name of the nested model"


def test_input_factory_input_has_constraints_directive() -> None:
    class Model(pydantic.BaseModel):
        name: typing.Annotated[str, pydantic.Field(min_length=1)]

    gql_input = InputFactory.make(Model)
    definition = gql_input.__strawberry_definition__
    assert len(definition.fields) == 1
    assert len(definition.fields[0].directives) == 1
    directive: FieldConstraintsDirective = definition.fields[0].directives[0]
    directive_schema: "StrawberrySchemaDirective" = directive.__strawberry_directive__
    assert directive_schema.graphql_name == "FieldConstraints"
    assert directive_schema.locations == [Location.INPUT_FIELD_DEFINITION]
    assert directive_schema.repeatable is True
    assert directive_schema.origin is FieldConstraintsDirective
    assert directive.min_length == 1


def test_input_factory_field_without_constraints_does_not_have_constraints_directive() -> None:
    class Model(pydantic.BaseModel):
        name: typing.Annotated[str, pydantic.Field(description="Name of the model")]

    gql_input = InputFactory.make(Model)
    definition = gql_input.__strawberry_definition__
    assert len(definition.fields) == 1
    assert len(definition.fields[0].directives) == 0


def test_input_factory_field_constraints_directive_values() -> None:
    class Model(pydantic.BaseModel):
        name: typing.Annotated[str, pydantic.Field(min_length=1, max_length=10, pattern=r"^\w+$")]
        age: typing.Annotated[int, pydantic.Field(gt=0, le=100, multiple_of=2)]
        cash: typing.Annotated[Decimal, pydantic.Field(max_digits=5, decimal_places=2, multiple_of=0.5, ge=0)]

    gql_input = InputFactory.make(Model)
    definition = gql_input.__strawberry_definition__
    assert len(definition.fields) == 3
    name_directive: FieldConstraintsDirective = definition.fields[0].directives[0]
    assert name_directive.min_length == 1
    assert name_directive.max_length == 10
    assert name_directive.pattern == r"^\w+$"
    assert name_directive.gt is None
    assert name_directive.ge is None
    assert name_directive.lt is None
    assert name_directive.le is None
    assert name_directive.max_digits is None
    assert name_directive.decimal_places is None
    assert name_directive.multiple_of is None

    age_directive: FieldConstraintsDirective = definition.fields[1].directives[0]
    assert age_directive.min_length is None
    assert age_directive.max_length is None
    assert age_directive.pattern is None
    assert age_directive.gt == 0
    assert age_directive.ge is None
    assert age_directive.lt is None
    assert age_directive.le == 100
    assert age_directive.max_digits is None
    assert age_directive.decimal_places is None
    assert age_directive.multiple_of == 2

    cash_directive: FieldConstraintsDirective = definition.fields[2].directives[0]
    assert cash_directive.min_length is None
    assert cash_directive.max_length is None
    assert cash_directive.pattern is None
    assert cash_directive.gt is None
    assert cash_directive.ge == 0
    assert cash_directive.lt is None
    assert cash_directive.le is None
    assert cash_directive.max_digits == 5
    assert cash_directive.decimal_places == 2
    assert cash_directive.multiple_of == 0.5
