import typing

from django.conf import settings as django_settings

SETTINGS_NAME: str = "STRAWBERRY_VERCAJK"


__all__ = [
    "app_settings",
    "StrawberryVercajkSettings",
]


class ListSettings(typing.TypedDict):
    """Settings of the Page."""

    # The maximum number of items which can be returned in a single page.
    MAX_PAGE_SIZE: typing.NotRequired[int]
    DEFAULT_PAGE_SIZE: typing.NotRequired[int]


class IDHasherSettings(typing.TypedDict):
    """Settings of the ID hasher."""

    ALPHABET: typing.NotRequired[str]
    MIN_LENGTH: typing.NotRequired[int]


class StrawberryVercajkSettings(typing.TypedDict):
    """Settings of the Strawberry vercajk app."""

    LIST: ListSettings
    ID_HASHER: IDHasherSettings


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


app_settings = AppSettings()
