import typing

from django.conf import settings as django_settings

SETTINGS_NAME: str = "STRAWBERRY_VERCAJK"


__all__ = [
    "app_settings",
    "StrawberryVercajkSettings",
]


class StrawberryVercajkSettings(typing.TypedDict):
    """Settings of the Strawberry vercajk app."""

    # The maximum number of items which can be returned in a single page.
    GRAPHQL_MAX_PAGE_SIZE: typing.NotRequired[int]


class AppSettings:
    @property
    def settings(self) -> StrawberryVercajkSettings:
        return getattr(django_settings, SETTINGS_NAME, {})

    @property
    def GRAPHQL_MAX_PAGE_SIZE(self) -> int:  # noqa: N802
        return self.settings.get("GRAPHQL_MAX_PAGE_SIZE", 100)


app_settings = AppSettings()
