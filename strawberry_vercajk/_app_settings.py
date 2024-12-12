__all__ = [
    "StrawberryVercajkSettings",
    "app_settings",
]

import typing

import pydantic
import pydantic_core
import strawberry
from django.conf import settings as django_settings

SETTINGS_NAME: str = "STRAWBERRY_VERCAJK"


class ListSettings(typing.TypedDict):
    """Settings of the Page."""

    # The maximum number of items which can be returned in a single page.
    MAX_PAGE_SIZE: typing.NotRequired[int]
    DEFAULT_PAGE_SIZE: typing.NotRequired[int]


class IDHasherSettings(typing.TypedDict):
    """Settings of the ID hasher."""

    ALPHABET: typing.NotRequired[str]
    MIN_LENGTH: typing.NotRequired[int]


class ValidationSettings(typing.TypedDict):
    """Settings of the validation."""

    PYDANTIC_FIELD_TO_GQL_INPUT_TYPE: typing.NotRequired[dict[type, type]]
    PYDANTIC_FIELD_TO_GQL_INPUT_TYPE_EXCLUDE_DEFAULTS: typing.NotRequired[bool]


class StrawberryVercajkSettings(typing.TypedDict):
    """Settings of the Strawberry vercajk app."""

    LIST: typing.NotRequired[ListSettings]
    ID_HASHER: typing.NotRequired[IDHasherSettings]
    VALIDATION: typing.NotRequired[ValidationSettings]


class AppListSettings:
    @property
    def MAX_PAGE_SIZE(self) -> int:  # noqa: N802
        return self._settings.get("MAX_PAGE_SIZE", 100)

    @property
    def DEFAULT_PAGE_SIZE(self) -> int:  # noqa: N802
        return self._settings.get("DEFAULT_PAGE_SIZE", 10)

    @property
    def _global_settings(self) -> StrawberryVercajkSettings:
        return getattr(django_settings, SETTINGS_NAME, {})

    @property
    def _settings(self) -> ListSettings:
        return self._global_settings.get("LIST", {})


class AppIDHasherSettings:
    @property
    def ALPHABET(self) -> str:  # noqa: N802
        return self._settings.get("ALPHABET", "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ")

    @property
    def MIN_LENGTH(self) -> int:  # noqa: N802
        return self._settings.get("MIN_LENGTH", 5)

    @property
    def _global_settings(self) -> StrawberryVercajkSettings:
        return getattr(django_settings, SETTINGS_NAME, {})

    @property
    def _settings(self) -> IDHasherSettings:
        return self._global_settings.get("ID_HASHER", {})


class AppValidationSettings:
    @property
    def PYDANTIC_TO_GQL_INPUT_TYPE(self) -> dict[type, type]:  # noqa: N802
        from strawberry_vercajk import HashedID

        if self.PYDANTIC_TO_GQL_INPUT_TYPE_EXCLUDE_DEFAULTS:
            defaults = {}
        else:
            defaults = {
                pydantic.EmailStr: str,
                pydantic.SecretStr: str,
                pydantic.SecretBytes: bytes,
                pydantic.AnyUrl: str,
                pydantic.HttpUrl: str,
                pydantic_core.MultiHostUrl: str,
                HashedID: strawberry.ID,
            }
        setting_values = self._settings.get("PYDANTIC_FIELD_TO_GQL_INPUT_TYPE", {})
        return defaults | setting_values

    @property
    def PYDANTIC_TO_GQL_INPUT_TYPE_EXCLUDE_DEFAULTS(self) -> bool:  # noqa: N802
        return self._settings.get("PYDANTIC_FIELD_TO_GQL_INPUT_TYPE_EXCLUDE_DEFAULTS", False)

    @property
    def _global_settings(self) -> StrawberryVercajkSettings:
        return getattr(django_settings, SETTINGS_NAME, {})

    @property
    def _settings(self) -> ValidationSettings:
        return self._global_settings.get("VALIDATION", {})


class AppSettings:
    @property
    def _settings(self) -> StrawberryVercajkSettings:
        return getattr(django_settings, SETTINGS_NAME, {})

    @property
    def LIST(self) -> AppListSettings:  # noqa: N802
        return AppListSettings()

    @property
    def ID_HASHER(self) -> AppIDHasherSettings:  # noqa: N802
        return AppIDHasherSettings()

    @property
    def VALIDATION(self) -> AppValidationSettings:  # noqa: N802
        return AppValidationSettings()


app_settings = AppSettings()
