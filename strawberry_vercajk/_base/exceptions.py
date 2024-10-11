import dataclasses
import typing

if typing.TYPE_CHECKING:
    import django.db.models


@dataclasses.dataclass
class ModelFieldDoesNotExistError(Exception):
    root_model: type["django.db.models.Model"]
    full_field_path: str
    model: type["django.db.models.Model"]
    field: str

    def __str__(self) -> str:
        msg = f"The `{self.full_field_path}` of `{self.root_model.__name__}` does not exist."
        if self.model != self.root_model:
            msg += f"\n\nProblem at: `{self.field}` field of `{self.model.__name__}`."
        return msg
