import enum

import strawberry

__all__ = [
    "ErrorInterface",
    "ErrorType",
    "ErrorConstraintType",
    "ErrorConstraintChoices",
    "MutationErrorInterface",
    "MutationErrorType",
    "ConstraintDataType",
]

from strawberry_vercajk._scalars import IntStr


class ConstraintDataType(enum.Enum):
    STRING = "string"
    INTEGER = "integer"


class ErrorConstraintChoices(enum.Enum):
    MIN_LENGTH = "min_length"
    MAX_LENGTH = "max_length"
    GT = "gt"
    GTE = "ge"
    LT = "lt"
    LTE = "le"
    MAX_DIGITS = "max_digits"
    DECIMAL_PLACES = "decimal_places"
    PATTERN = "pattern"
    MULTIPLE_OF = "multiple_of"

    def get_data_type(self) -> "ConstraintDataType":
        if self in {
            ErrorConstraintChoices.PATTERN,
        }:
            return ConstraintDataType.STRING
        return ConstraintDataType.INTEGER


@strawberry.type
class ErrorConstraintType:
    code: ErrorConstraintChoices
    value: IntStr
    data_type: ConstraintDataType


@strawberry.interface(name="ErrorInterface", description="Common interface for all errors.")
class ErrorInterface:
    location: list[IntStr] = strawberry.field(default_factory=list)  # empty list means non-field error;
    code: str
    message: str
    constraints: list[ErrorConstraintType] = strawberry.field(
        description="Constraints which were violated.",
        default_factory=list,
    )


@strawberry.type(name="Error", description="Error related to input validation.")
class ErrorType(ErrorInterface):
    pass


@strawberry.type(description="Interface for errors which occurred during a mutation.")
class MutationErrorInterface:
    errors: list[ErrorInterface]


@strawberry.type(name="MutationError", description="Errors which occurred during a mutation.")
class MutationErrorType(MutationErrorInterface):
    pass
