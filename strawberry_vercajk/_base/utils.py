import django.core.exceptions
import django.db.models
import pydantic

from strawberry_vercajk._base import exceptions


def check_django_field_exists(model: type["django.db.models.Model"], field_path: str) -> None:
    """
    Checks if the field exists on the model.
    :param model: Django database model
    :param field_path: Field name, potentially with a related model path (e.g. `related_model__field`)
    :raises ModelFieldDoesNotExistError: If the field does not exist on the model.
    """
    field_path_sep: list[str] = field_path.split("__")
    django_model_ = model
    for field in field_path_sep:
        try:
            model_field: django.db.models.Field = django_model_._meta.get_field(field)  # noqa: SLF001
        except django.core.exceptions.FieldDoesNotExist as e:
            raise exceptions.ModelFieldDoesNotExistError(
                root_model=model,
                full_field_path=field_path,
                model=django_model_,
                field=field,
            ) from e
        if model_field.is_relation:
            django_model_ = model_field.related_model


def check_pydantic_field_exists(model: type["pydantic.BaseModel"], field_path: str) -> None:
    """
    Checks if the field exists on the pydantic model.
    :param model: Pydantic model
    :param field_path: Field name, potentially with a related model path (e.g. `related_model.field`)
    :raises ModelFieldDoesNotExistError: If the field does not exist on the model.
    """
    field_path_sep: list[str] = field_path.split(".")
    pyd_model = model
    for field in field_path_sep:
        try:
            model_field = pyd_model.__pydantic_fields__[field]
        except KeyError as e:
            raise exceptions.ModelFieldDoesNotExistError(
                root_model=model,
                full_field_path=field_path,
                model=pyd_model,
                field=field,
            ) from e
        if isinstance(model_field, pydantic.BaseModel):
            pyd_model = model_field
