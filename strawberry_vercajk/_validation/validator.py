__all__ = [
    "AsyncFieldValidator",
    "AsyncValidatedInput",
    "InputValidator",
    "ValidatedInput",
    "async_model_validator",
    "build_errors",
    "pydantic_to_input_type",
    "set_gql_params",
    "validation_context",
]

import contextlib
import contextvars
import logging
import typing
import warnings
from typing import Any

import pydantic
import pydantic_core
from strawberry.utils.str_converters import to_camel_case

from strawberry_vercajk._base.types import UNSET
from strawberry_vercajk._validation import constants, gql_types

if typing.TYPE_CHECKING:
    import strawberry.types.base

logger = logging.getLogger(__name__)
_validation_context_var = contextvars.ContextVar("_validation_context_var", default=None)


@contextlib.contextmanager
def validation_context(value: dict[str, typing.Any]) -> typing.Iterator[None]:
    token: contextvars.Token = _validation_context_var.set(value)
    try:
        yield
    finally:
        _validation_context_var.reset(token)


def set_gql_params[V](
    *,
    name: str,
) -> typing.Callable[[type[V]], type[V]]:
    """
    Decorator to set gql params on the input type, used when converting pydantic validators to strawberry input types
    via `pydantic_to_input_type` (or `InputFactory.make`).
    :param name: The name of the gql type.

    Example:
        >>> @set_gql_params(name="CustomerCreateInput")
        ... class CustomerCreateWithAddressInput(ValidatedInput):
        ...     ...

    """

    def wrapper(validator: type[V]) -> type[V]:
        setattr(validator, constants.INPUT_VALIDATOR_GQL_NAME, name)
        return validator

    return wrapper


class ValidatedInput[CleanDataType: "pydantic.BaseModel"]:
    """A class to be used to validate input data. Used on `strawberry.experimental.pydantic.input` types."""

    __clean_data: CleanDataType | None = UNSET
    __errors: list["gql_types.ErrorInterface"] = UNSET
    __original_error: pydantic.ValidationError | None = UNSET
    __strawberry_definition__: typing.ClassVar["strawberry.types.base.StrawberryObjectDefinition"]
    # _pydantic_type: type[CleanDataType]  # set by strawberry - use `get_validator` method instead

    @classmethod
    def __class_getitem__(cls, item: type[CleanDataType] | typing.TypeVar) -> type["ValidatedInput[CleanDataType]"]:
        if isinstance(item, typing.TypeVar):
            # Type checking - workaround for cases as
            # `def pydantic_to_input_type[T: "pydantic.BaseModel"](...) -> type[ValidatedInput[T]]: ...`
            return cls
        from strawberry_vercajk import InputFactory

        if issubclass(item, InputValidator):
            async_validators = item.get_async_validators()
            if async_validators["model"] or async_validators["fields"]:
                raise TypeError(
                    "Cannot create input type for async validators. "
                    "Use `AsyncValidatedInput` instead of `ValidatedInput`.",
                )
        return InputFactory.make(item)

    def clean(
        self,
        context: dict | None = None,
    ) -> list["gql_types.ErrorInterface"]:
        """
        Cleans (validates) the input data and returns the (potential) errors.
        """
        if context is None:
            context = {}

        if self.__clean_data is UNSET:
            with validation_context(context):
                try:
                    # The `to_pydantic` method is used by strawberry to convert the input data to a pydantic model,
                    # but we need to override it.
                    # See `to_pydantic` method in `InputFactory.make` for more details.
                    cleaned_data: CleanDataType = self.to_pydantic(is_inner=False)
                except pydantic.ValidationError as e:
                    self.clean_data = None
                    self.original_error = e
                    self.errors = build_errors(e)
                else:
                    self.errors = []
                    self.original_error = None
                    self.clean_data = cleaned_data
        return self.errors

    @property
    def clean_data(self) -> CleanDataType:
        if self.__clean_data is UNSET:
            raise ValueError("You must call `clean` before accessing `clean_data`.")
        if self.__clean_data is None:
            raise ValueError("The data did not pass the validation.")
        return self.__clean_data

    @clean_data.setter
    def clean_data(self, value: CleanDataType) -> None:
        if self.__clean_data is not UNSET:
            raise AttributeError("Cannot re-set clean_data attribute - it is read-only.")
        self.__clean_data = value

    @property
    def errors(self) -> list["gql_types.ErrorInterface"]:
        if self.__errors is UNSET:
            raise ValueError("You must call `clean` method before accessing `errors`.")
        return self.__errors

    @errors.setter
    def errors(self, value: list["gql_types.ErrorInterface"]) -> None:
        if self.__errors is not UNSET:
            raise AttributeError("Cannot re-set errors attribute - it is read-only.")
        self.__errors = value

    @property
    def original_error(self) -> pydantic.ValidationError | None:
        if self.__original_error is UNSET:
            raise ValueError("You must call `clean` method before accessing `original_error`.")
        return self.__original_error

    @original_error.setter
    def original_error(self, value: pydantic.ValidationError) -> None:
        if self.__original_error is not UNSET:
            raise AttributeError("Cannot re-set original_error attribute - it is read-only.")
        self.__original_error = value

    @classmethod
    def get_validator(cls) -> type[CleanDataType]:
        try:
            return getattr(cls, constants.INPUT_VALIDATOR_ATTR_NAME)
        except AttributeError as e:
            raise AttributeError(
                f"Cannot find validator on {cls.__name__}. "
                f"Make sure to use `{cls.__name__}[ValidatorCls]` to create the input type from the ValidatorCls.",
            ) from e


class AsyncValidatedInput[CleanDataType: "InputValidator"](ValidatedInput[CleanDataType]):
    """
    Like `ValidatedInput`, but for validators which use async validators.
    See `AsyncFieldValidator` and `@async_model_validator`.
    """

    __clean_data: CleanDataType | None = UNSET
    __errors: list["gql_types.ErrorInterface"] | None = UNSET

    @classmethod
    def __class_getitem__(
        cls,
        item: type[CleanDataType] | typing.TypeVar,
    ) -> type["AsyncValidatedInput[CleanDataType]"]:
        if isinstance(item, typing.TypeVar):
            # Type checking - workaround for cases as
            # `def pydantic_to_input_type[T: "pydantic.BaseModel"](...) -> type[ValidatedInput[T]]: ...`
            return cls
        from strawberry_vercajk import InputFactory

        if not issubclass(item, InputValidator):
            raise TypeError(f"`{item}` must inherit from `{InputValidator.__name__}`.")
        return InputFactory.make(item, async_=True)

    async def clean(
        self,
        context: dict | None = None,
    ) -> list["gql_types.ErrorInterface"]:
        """
        Cleans (validates) the input data and returns the (potential) errors.
        """
        if context is None:
            context = {}

        if self.__clean_data is UNSET:
            with validation_context(context):
                try:
                    # The `to_pydantic` method is used by strawberry to convert the input data to a pydantic model,
                    # but we need to override it.
                    # See `to_pydantic` method in `InputFactory.make` for more details.
                    cleaned_data: CleanDataType = self.to_pydantic(is_inner=False)
                    async_errs = await self._run_async_clean(cleaned_data)
                    if async_errs:
                        raise pydantic.ValidationError.from_exception_data(
                            "Validation failed",
                            line_errors=async_errs,
                        )
                except pydantic.ValidationError as e:
                    self.clean_data = None
                    self.errors = build_errors(e)
                else:
                    self.errors = []
                    self.clean_data = cleaned_data
        return self.errors

    @classmethod
    async def _run_async_clean(
        cls,
        cleaned_data: CleanDataType,
        *,
        _loc_prepend: tuple[str | int, ...] = (),
    ) -> list["pydantic_core.InitErrorDetails"]:
        """
        Run async validators on the cleaned data.
        """
        errors = await cls._run_async_clean_field_validators(cleaned_data, _loc_prepend=_loc_prepend)
        if errors:
            # If there are errors in fields, don't even run the full-model validators.
            return errors
        errors.extend(await cls._run_async_clean_model_validators(cleaned_data, _loc_prepend=_loc_prepend))
        return errors

    @classmethod
    async def _run_async_clean_field_validators(
        cls,
        cleaned_data: CleanDataType,
        *,
        _loc_prepend: tuple[str | int, ...] = (),
    ) -> list["pydantic_core.InitErrorDetails"]:
        # TODO asyncio TaskGroup to run all validators in parallel
        # TODO cache these, so we don't have to loop through all fields and all metadata every time
        errors: list[pydantic_core.InitErrorDetails] = []
        validators = cleaned_data.get_async_validators()["fields"]
        for field_name, field_info in cleaned_data.__pydantic_fields__.items():
            if field_info.annotation is pydantic.BaseModel:
                inner_errors = await cls._run_async_clean(
                    cleaned_data.__getattribute__(field_name),
                    _loc_prepend=(*_loc_prepend, field_name),
                )
                errors.extend(inner_errors)
                if inner_errors:
                    # Don't run the field validators if the inner model has errors.
                    continue
            for validator in validators.get(field_name, []):
                field_value = cleaned_data.__getattribute__(field_name)
                try:
                    await validator(field_value)  # TODO - pass in info if possible somehow
                except (pydantic.ValidationError, pydantic_core.PydanticCustomError) as e:
                    errors.extend(
                        cls.__pydantic_error_to_init_error_details(
                            e,
                            field_name=field_name,
                            field_value=field_value,
                            loc_prepend=_loc_prepend,
                        ),
                    )
        return errors

    @classmethod
    async def _run_async_clean_model_validators(
        cls,
        cleaned_data: CleanDataType,
        *,
        _loc_prepend: tuple[str | int, ...] = (),
    ) -> list[pydantic_core.InitErrorDetails]:
        errors: list[pydantic_core.InitErrorDetails] = []
        validator_method_names = cleaned_data.get_async_validators()["model"]
        for validator_method_name in validator_method_names:
            try:
                await getattr(cleaned_data, validator_method_name)()
            except (pydantic.ValidationError, pydantic_core.PydanticCustomError) as e:
                errors.extend(
                    cls.__pydantic_error_to_init_error_details(
                        e,
                        field_name=None,
                        field_value=None,
                        loc_prepend=_loc_prepend,
                    ),
                )
        return errors

    @staticmethod
    def __pydantic_error_to_init_error_details(
        e: pydantic.ValidationError | pydantic_core.InitErrorDetails,
        *,
        field_name: str | None,
        field_value: typing.Any | None,  # noqa: ANN401
        loc_prepend: tuple[str | int, ...] = (),
    ) -> list[pydantic_core.InitErrorDetails]:
        """
        Convert a pydantic ValidationError to a list of InitErrorDetails.
        """
        errors: list[pydantic_core.InitErrorDetails] = []
        if isinstance(e, pydantic.ValidationError):
            for err in e.errors():
                err: pydantic_core.ErrorDetails
                errors.append(
                    pydantic_core.InitErrorDetails(
                        type=pydantic_core.PydanticCustomError(
                            typing.cast("typing.LiteralString", err["type"]),
                            typing.cast("typing.LiteralString", err["msg"]),
                        ),
                        loc=loc_prepend + err["loc"],
                        input=err["input"],
                    ),
                )
        elif isinstance(e, pydantic_core.PydanticCustomError):
            errors.append(
                pydantic_core.InitErrorDetails(
                    type=e,
                    loc=loc_prepend + ((field_name,) if field_name else ()),
                    input=field_value,
                    ctx=e.context,
                ),
            )
        else:
            raise TypeError(f"Expected pydantic.ValidationError or pydantic_core.PydanticCustomError, got {type(e)}.")
        return errors


class AsyncFieldValidator:
    """
    Abstract class for async field validators.
    Used to validate fields in the class via functions which are async.
    Beware that unlike the "classical" pydantic validators, AsyncFieldValidators are called after the pydantic model
    is instantiated and passes the pydantic validation.

    Example:
        Define the field validator:
        >>> async def username_not_pepa(value: str) -> str:
        ...     if value == "pepa":
        ...         raise pydantic_core.PydanticCustomError(
        ...             "invalid_name",
        ...             "There can be only one pepa, and you are not it.",
        ...         )
        ...     return value
        # And use it in the input class:
        >>> class UserCreateInput(strawberry_vercajk.InputValidator):
        ...     username: typing.Annotated[
        ...         str,
        ...         strawberry_vercajk.AsyncFieldValidator(username_not_pepa)
        ...     ]

    """

    def __init__(
        self,
        validator: typing.Callable[[typing.Any], typing.Awaitable[typing.Any]],
        /,
    ) -> None:
        """
        Initialize the validator.
        :param validator: The validator function to be called.
        """
        self.validator = validator

    async def __call__(self, value: typing.Any) -> typing.Any:  # noqa: ANN401
        """
        Validate the value and return it.
        """
        return await self.validator(value)


def async_model_validator[M: typing.Callable[[typing.Any], typing.Awaitable[None]]](
    method: M | None = None,
    /,
) -> M:
    """
    Decorator to mark a method as an async model validator.
    Method decorated with this decorator will be called after all the field validators have been called.
    If the method raises a `pydantic.ValidationError` or `pydantic_core.PydanticCustomError`, the error will be added
    to the list of errors.
    The method must be a coroutine function.

    Example:
        >>> class UserCreateInput(AsyncValidatedInput):
        ...     email: pydantic.EmailStr
        ...     name: str
        ...     age: int
        ...
        ...     @async_model_validator()
        ...     async def validate_email(self) -> None:
        ...         if not self.email.endswith("@example.com"):
        ...             raise pydantic_core.PydanticCustomError(
        ...                 "invalid_email",
        ...                 "Email must end with @example.com",
        ...             )
        ...         return self

    """

    def wrapper(method_: M, /) -> M:
        setattr(method_, constants.ASYNC_MODEL_VALIDATOR_ATTR_NAME, True)
        return method_

    if method is not None:
        # If the method is passed directly, return the wrapped method.
        return wrapper(method)
    return wrapper


class _ModelAsyncValidatorsCollection(typing.TypedDict):
    model: list[str]  # names of the model validator methods
    fields: dict[str, list[typing.Callable[[typing.Any], typing.Awaitable[typing.Any]]]]


class InputValidator(pydantic.BaseModel):
    """A class used to validate input data."""

    model_config = pydantic.ConfigDict(
        arbitrary_types_allowed=True,
        frozen=True,  # makes the instance immutable - once the data is validated, it should not be changed directly
    )

    # noinspection PyMissingConstructor,PyMethodParameters
    def __init__(__pydantic_self__, **data: typing.Any) -> None:  # noqa: N805 ANN401
        """
        Override __init__ to add a validation context (see validation_context context manager).
        Copied from:
        https://docs.pydantic.dev/latest/concepts/validators/#using-validation-context-with-basemodel-initialization
        """
        __pydantic_self__.__pydantic_validator__.validate_python(
            data,
            self_instance=__pydantic_self__,
            context=_validation_context_var.get(),
        )

    @typing.override
    @classmethod
    def __pydantic_init_subclass__(cls, **kwargs: Any) -> None:
        validators_collection: _ModelAsyncValidatorsCollection = {"model": [], "fields": {}}
        for method_name in dir(cls):
            if method_name.startswith("__"):
                continue
            method = getattr(cls, method_name)
            if getattr(method, constants.ASYNC_MODEL_VALIDATOR_ATTR_NAME, False):
                validators_collection["model"].append(method_name)
        for field_name, field_info in cls.__pydantic_fields__.items():
            for meta in field_info.metadata:
                if isinstance(meta, AsyncFieldValidator):
                    validators_collection["fields"].setdefault(field_name, []).append(meta.validator)
        setattr(cls, constants.INPUT_VALIDATOR_ASYNC_VALIDATORS_ATTR_NAME, validators_collection)

    @classmethod
    def get_async_validators(cls) -> _ModelAsyncValidatorsCollection:
        return getattr(cls, constants.INPUT_VALIDATOR_ASYNC_VALIDATORS_ATTR_NAME)


def pydantic_to_input_type[T: "pydantic.BaseModel"](  # TODO - remove and internally use InputFactory directly
    validator_cls: type[T],
    /,
    name: typing.LiteralString | None = None,
) -> type[ValidatedInput[T]]:
    """
    Return a strawberry input type for given validator.
    """
    warnings.warn(
        "Use `ValidatedInput[<validatorCls>]` instead of `pydantic_to_input_type(<validatorCls>)`. "
        "This function will be removed in the future. "
        "To set the gql name, use `@set_gql_params(name='...')` decorator on the `validatorCls`.",
        DeprecationWarning,
        stacklevel=2,
    )
    from strawberry_vercajk._validation.input_factory import InputFactory

    return InputFactory.make(validator_cls, name=name)


def build_errors(exc: "pydantic.ValidationError") -> list["gql_types.ErrorInterface"]:
    errors: list[gql_types.ErrorInterface] = []
    locations_with_type_union_errors: set[tuple[str, ...]] = set()
    for error in exc.errors():
        error_ctx = error.get("ctx", {})
        loc = error.get("loc", [])
        constraints: list[gql_types.ErrorConstraintType] = []
        for ctx_code, ctx_value in error_ctx.items():
            if ctx_code not in gql_types.ErrorConstraintChoices:
                continue
            ctx_code: gql_types.ErrorConstraintChoices = gql_types.ErrorConstraintChoices(ctx_code)  # noqa: PLW2901
            constraints.append(
                gql_types.ErrorConstraintType(
                    code=ctx_code,
                    value=str(ctx_value),
                    data_type=ctx_code.get_data_type(),
                ),
            )

        location: list[str | int] = []
        loc_len = len(loc)
        has_type_union_error: bool = False
        for l_idx, l in enumerate(loc, 1):  # noqa: E741
            if l_idx == loc_len and isinstance(l, str) and "[" in l:
                # A special case, when the pydantic field is a union of types which have more validators,
                # the last location element is the validator in which the error occurred.
                # For example, if we have a field
                #   email: pydantic.EmailStr | typing.Literal[""]
                # and we pass in a value "some_invalid_email", pydantic will throw two errors with these locations:
                #   - ("email", "function-after[Validate(), str]")
                #   - ("email", "literal['']")
                # We don't want to include the last part of the location in the error message.
                # From my observation, the last part always seems to include "[" character, which can
                # never be in the field name - using this to determine if we should skip the last part.
                # See test_specific_validator_stripped_from_error_location.
                has_type_union_error = True
                continue
            if isinstance(l, str):
                location.append(to_camel_case(l))
            else:
                location.append(l)

        if has_type_union_error:
            if tuple(location) in locations_with_type_union_errors:
                # See comment above.
                # We only keep the first error for the same location from the errors caused by type union.
                # This is so we don't confuse the user with multiple errors for the same field which may even be
                # contradictory in some cases.
                # This relies on the programmer to place the more specific validators first in the union, so
                # for example, `email: pydantic.EmailStr | typing.Literal[""]` and not the other way around.
                continue
            locations_with_type_union_errors.add(tuple(location))

        errors.append(
            gql_types.ErrorType(
                code=error["type"],
                message=error["msg"],
                location=location,
                constraints=constraints,
            ),
        )
    return errors
