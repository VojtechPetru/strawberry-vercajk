import typing

import pydantic
import pytest

import strawberry_vercajk


def test_validated_input() -> None:
    class Model(pydantic.BaseModel):
        name: str
        age: int

    input_type = strawberry_vercajk.pydantic_to_input_type(Model)

    input_data = input_type(name="John", age=20)
    errors = input_data.clean()
    assert errors == []
    assert type(input_data.clean_data) is Model
    assert input_data.clean_data.model_dump() == {"name": "John", "age": 20}


def test_validated_input_with_constraints_ok() -> None:
    class Model(pydantic.BaseModel):
        name: typing.Annotated[str, pydantic.Field(max_length=10)]
        age: int

    input_type = strawberry_vercajk.pydantic_to_input_type(Model)

    input_data = input_type(name="John", age=20)
    errors = input_data.clean()
    assert errors == []
    assert type(input_data.clean_data) is Model
    assert input_data.clean_data.model_dump() == {"name": "John", "age": 20}


def test_validated_input_with_constraints_error() -> None:
    class Model(pydantic.BaseModel):
        name: typing.Annotated[str, pydantic.Field(max_length=2)]
        age: typing.Annotated[int, pydantic.Field(lt=10)]

    input_type = strawberry_vercajk.pydantic_to_input_type(Model)

    input_data = input_type(name="John Doe", age=20)
    errors = input_data.clean()
    assert len(errors) == 2
    assert type(errors[0]) is strawberry_vercajk.ErrorType
    assert type(errors[1]) is strawberry_vercajk.ErrorType
    assert errors[0].code == "string_too_long"
    assert errors[0].message == "String should have at most 2 characters"
    assert errors[0].location == ["name"]
    assert errors[0].constraints == [
        strawberry_vercajk.ErrorConstraintType(
            code=strawberry_vercajk.ErrorConstraintChoices.MAX_LENGTH,
            value="2",
            data_type=strawberry_vercajk.ConstraintDataType.INTEGER,
        )
    ]
    assert errors[1].code == "less_than"
    assert errors[1].message == "Input should be less than 10"
    assert errors[1].location == ["age"]
    assert errors[1].constraints == [
        strawberry_vercajk.ErrorConstraintType(
            code=strawberry_vercajk.ErrorConstraintChoices.LT,
            value="10",
            data_type=strawberry_vercajk.ConstraintDataType.INTEGER,
        )
    ]

    with pytest.raises(ValueError) as err:
        assert input_data.clean_data
    assert str(err.value) == "The data did not pass the validation."


def test_validated_input_with_nested_ok() -> None:
    class NestedModel(pydantic.BaseModel):
        name: str

    class Model(pydantic.BaseModel):
        nested: NestedModel

    input_type = strawberry_vercajk.pydantic_to_input_type(Model)

    input_data = input_type(nested={"name": "John"})
    errors = input_data.clean()
    assert errors == []
    assert type(input_data.clean_data) is Model
    assert type(input_data.clean_data.nested) is NestedModel
    assert input_data.clean_data.model_dump() == {"nested": {"name": "John"}}


def test_validated_input_with_nested_error() -> None:
    class NestedModel(pydantic.BaseModel):
        name: typing.Annotated[str, pydantic.Field(max_length=2)]

    class Model(pydantic.BaseModel):
        nested: NestedModel

    input_type = strawberry_vercajk.pydantic_to_input_type(Model)

    input_data = input_type(nested={"name": "John Doe"})
    errors = input_data.clean()
    assert len(errors) == 1
    assert type(errors[0]) is strawberry_vercajk.ErrorType
    assert errors[0].code == "string_too_long"
    assert errors[0].message == "String should have at most 2 characters"
    assert errors[0].location == ["nested", "name"]
    assert errors[0].constraints == [
        strawberry_vercajk.ErrorConstraintType(
            code=strawberry_vercajk.ErrorConstraintChoices.MAX_LENGTH,
            value="2",
            data_type=strawberry_vercajk.ConstraintDataType.INTEGER,
        )
    ]

    with pytest.raises(ValueError) as err:
        assert input_data.clean_data
    assert str(err.value) == "The data did not pass the validation."


def test_validated_input_with_list_ok() -> None:
    class Model(pydantic.BaseModel):
        names: list[str]

    input_type = strawberry_vercajk.pydantic_to_input_type(Model)

    input_data = input_type(names=["John", "Doe"])
    errors = input_data.clean()
    assert errors == []
    assert type(input_data.clean_data) is Model
    assert input_data.clean_data.model_dump() == {"names": ["John", "Doe"]}


def test_validated_input_with_list_error() -> None:
    class Model(pydantic.BaseModel):
        names: typing.Annotated[list[str], pydantic.Field(min_length=2)]

    input_type = strawberry_vercajk.pydantic_to_input_type(Model)

    input_data = input_type(names=["John"])
    errors = input_data.clean()
    assert len(errors) == 1
    assert type(errors[0]) is strawberry_vercajk.ErrorType
    assert errors[0].code == "too_short"
    assert errors[0].message == "List should have at least 2 items after validation, not 1"
    assert errors[0].location == ["names"]
    assert errors[0].constraints == [
        strawberry_vercajk.ErrorConstraintType(
            code=strawberry_vercajk.ErrorConstraintChoices.MIN_LENGTH,
            value="2",
            data_type=strawberry_vercajk.ConstraintDataType.INTEGER,
        )
    ]

    with pytest.raises(ValueError) as err:
        assert input_data.clean_data
    assert str(err.value) == "The data did not pass the validation."


def test_multiple_nested_inputs_with_errors() -> None:
    class NestedModel(pydantic.BaseModel):
        name: typing.Annotated[str, pydantic.Field(max_length=2)]

    class NestedModel2(pydantic.BaseModel):
        age: typing.Annotated[int, pydantic.Field(lt=10)]

    class Model(pydantic.BaseModel):
        nested: NestedModel
        nested2: NestedModel2

    input_type = strawberry_vercajk.pydantic_to_input_type(Model)
    input_data = input_type(nested={"name": "John Doe"}, nested2={"age": 20})
    errors = input_data.clean()
    assert len(errors) == 2
    assert type(errors[0]) is strawberry_vercajk.ErrorType
    assert errors[0].code == "string_too_long"
    assert errors[0].message == "String should have at most 2 characters"
    assert errors[0].location == ["nested", "name"]
    assert errors[0].constraints == [
        strawberry_vercajk.ErrorConstraintType(
            code=strawberry_vercajk.ErrorConstraintChoices.MAX_LENGTH,
            value="2",
            data_type=strawberry_vercajk.ConstraintDataType.INTEGER,
        )
    ]
    assert type(errors[1]) is strawberry_vercajk.ErrorType
    assert errors[1].code == "less_than"
    assert errors[1].message == "Input should be less than 10"
    assert errors[1].location == ["nested2", "age"]
    assert errors[1].constraints == [
        strawberry_vercajk.ErrorConstraintType(
            code=strawberry_vercajk.ErrorConstraintChoices.LT,
            value="10",
            data_type=strawberry_vercajk.ConstraintDataType.INTEGER,
        )
    ]
